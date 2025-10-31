#!/usr/bin/env python3
"""
Auto-extract VTT-ready wall lines from a red-traced map.

Pipeline (grid-agnostic):
1) Load → HSV red threshold → clean (close+open).
2) Dilate (~2 px) to seal micro gaps.
3) Skeletonize → trace 8-connected polylines.
4) Simplify (RDP).
5) Connect: snap endpoint↔endpoint and endpoint→polyline (T-junctions).
6) Drop short stubs → tiny cleanup RDP.
7) Save: overlays (blue on original) + "blue-only" (transparent & white).
8) Optional: export polylines as JSON (pixels).

Requires: opencv-python, numpy, scikit-image
"""
import argparse, json, math, os
from pathlib import Path
import cv2, numpy as np
from skimage.morphology import thin

# ---------- Utilities ----------
def red_mask_hsv(img_rgb, s_min=110, v_min=60):
    hsv = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2HSV)
    m1 = cv2.inRange(hsv, (0, s_min, v_min), (10, 255, 255))
    m2 = cv2.inRange(hsv, (170, s_min, v_min), (179, 255, 255))
    return cv2.bitwise_or(m1, m2)

def draw_overlay(img_bgr, polys, color=(255,120,0), thick=2):
    """Draw polylines on BGR image (for overlay output)."""
    result = img_bgr.copy()
    for poly in polys:
        if len(poly)<2: continue
        cv2.polylines(result, [np.int32(poly).reshape(-1,1,2)], False, color, thick, cv2.LINE_AA)
    return result

def clean_mask(mask, close_k=5, open_k=3):
    if close_k: mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((close_k,close_k),np.uint8))
    if open_k:  mask = cv2.morphologyEx(mask,  cv2.MORPH_OPEN,  np.ones((open_k,open_k),np.uint8))
    return mask

def rdp(points, eps):
    """Ramer–Douglas–Peucker on list[(x,y)]."""
    if len(points) < 3: return points
    def dpt(p,a,b):
        ax,ay=a; bx,by=b; px,py=p
        if ax==bx and ay==by: return math.hypot(px-ax, py-ay)
        t=max(0,min(1,((px-ax)*(bx-ax)+(py-ay)*(by-ay))/((bx-ax)**2+(by-ay)**2)))
        q=(ax+t*(bx-ax), ay+t*(by-ay)); return math.hypot(px-q[0], py-q[1])
    imax, dmax = 0, 0.0
    for i in range(1,len(points)-1):
        d = dpt(points[i], points[0], points[-1])
        if d>dmax: imax, dmax = i, d
    if dmax>eps:
        a = rdp(points[:imax+1], eps)
        b = rdp(points[imax:],   eps)
        return a[:-1]+b
    return [points[0], points[-1]]

def simplify_collinear(points, tolerance=1.0):
    """Remove points that are nearly collinear with their neighbors.
    
    For each point, check if it lies on (or very close to) the line 
    between its predecessor and successor. If so, remove it.
    Iterates until no more points can be removed.
    """
    if len(points) <= 2:
        return points
    
    changed = True
    result = list(points)
    
    while changed:
        changed = False
        simplified = [result[0]]  # Always keep first point
        
        for i in range(1, len(result) - 1):
            prev = simplified[-1]
            curr = result[i]
            next_pt = result[i + 1]
            
            # Calculate perpendicular distance from curr to line prev->next_pt
            px, py = curr
            ax, ay = prev
            bx, by = next_pt
            
            # Vector from a to b
            dx, dy = bx - ax, by - ay
            len_sq = dx * dx + dy * dy
            
            if len_sq < 1e-10:  # prev and next are essentially the same point
                continue
            
            # Perpendicular distance
            t = ((px - ax) * dx + (py - ay) * dy) / len_sq
            t = max(0, min(1, t))  # Clamp to segment
            closest_x = ax + t * dx
            closest_y = ay + t * dy
            dist = math.hypot(px - closest_x, py - closest_y)
            
            # Only keep the point if it's far enough from the line
            if dist > tolerance:
                simplified.append(curr)
            else:
                changed = True  # We removed a point, so iterate again
        
        simplified.append(result[-1])  # Always keep last point
        result = simplified
    
    return result

def lines_only_rgba(polys, size, thick=2, color_bgr=(255,120,0), white_bg=False, vertices_only=False, lines_and_vertices=False):
    H,W = size; bgr = np.zeros((H,W,3), np.uint8)
    for p in polys:
        if len(p)<2: continue
        if vertices_only:
            # Draw only the vertex points
            for point in p:
                x, y = int(point[0]), int(point[1])
                cv2.circle(bgr, (x, y), max(2, thick), color_bgr, -1, cv2.LINE_AA)
        elif lines_and_vertices:
            # Draw lines first
            cv2.polylines(bgr, [np.int32(p).reshape(-1,1,2)], False, color_bgr, thick, cv2.LINE_AA)
            # Then draw vertices on top
            for point in p:
                x, y = int(point[0]), int(point[1])
                cv2.circle(bgr, (x, y), max(3, thick+1), color_bgr, -1, cv2.LINE_AA)
        else:
            # Just draw solid lines
            cv2.polylines(bgr, [np.int32(p).reshape(-1,1,2)], False, color_bgr, thick, cv2.LINE_AA)
    if white_bg:
        bgra = np.dstack([bgr, np.full((H,W),255,np.uint8)])
    else:
        a = (bgr.sum(2)>0).astype(np.uint8)*255
        bgra = np.dstack([bgr, a])
    return bgra

# ---------- Skeleton → polylines ----------
def skeleton_polylines(mask, dilate_px=2):
    if dilate_px>0:
        k = 2*dilate_px+1
        mask = cv2.dilate(mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(k,k)), 1)
    skel = thin(mask>0).astype(np.uint8)  # 1-px strokes

    idx = np.argwhere(skel>0)
    pix = {(int(y),int(x)) for y,x in idx}       # store as (row,col)
    
    def nbrs(p):
        r,c=p
        # 8-connected neighborhood
        return [(r+dr,c+dc) for dr in (-1,0,1) for dc in (-1,0,1)
                if (dr or dc) and (r+dr,c+dc) in pix]
    
    deg = {p:len(nbrs(p)) for p in pix}
    endpoints = [p for p,d in deg.items() if d==1]
    vis=set()

    def trace(start):
        path=[start]; vis.add(start)
        n=[q for q in nbrs(start) if q not in vis]
        if not n: return path
        cur=n[0]; prev=start; path.append(cur); vis.add(cur)
        while True:
            n=[q for q in nbrs(cur) if q!=prev and q not in vis]
            if len(nbrs(cur))!=2 or not n: break
            nxt=n[0]; path.append(nxt); vis.add(nxt); prev,cur=cur,nxt
        return path

    lines=[]
    for ep in endpoints:
        if ep in vis: continue
        p=[(q[1],q[0]) for q in trace(ep)];  # (x,y)
        if len(p)>=2: lines.append(p)
    # cycles
    for p0 in list(pix):
        if p0 in vis: continue
        if deg.get(p0,0)==2:
            p=[(q[1],q[0]) for q in trace(p0)]
            if len(p)>=2: lines.append(p)
    return lines

# ---------- Connect gaps (vector) ----------
def poly_length(poly): return sum(math.hypot(poly[i+1][0]-poly[i][0], poly[i+1][1]-poly[i][1]) for i in range(len(poly)-1))
def nearest_on_seg(p,a,b):
    ax,ay=a; bx,by=b; px,py=p; dx,dy=bx-ax,by-ay; den=dx*dx+dy*dy
    if den==0: return a, math.hypot(px-ax,py-ay), 0.0
    t=max(0.0,min(1.0,((px-ax)*dx+(py-ay)*dy)/den)); q=(ax+t*dx, ay+t*dy)
    return q, math.hypot(px-q[0],py-q[1]), t
def insert_point(poly, i, t):
    ax,ay=poly[i]; bx,by=poly[i+1]; q=(ax+t*(bx-ax), ay+t*(by-ay))
    return poly[:i+1]+[q]+poly[i+1:]

def connect_polylines(polys, snap_dist=6.0, min_len=12.0):
    # 1) endpoint↔endpoint snap/merge
    changed=True
    while changed:
        changed=False; n=len(polys); used=[False]*n
        for i in range(n):
            if used[i]: continue
            e1=(polys[i][0], polys[i][-1])
            for j in range(i+1,n):
                if used[j]: continue
                e2=(polys[j][0], polys[j][-1])
                for a in (0,1):
                    for b in (0,1):
                        d=math.hypot(e1[a][0]-e2[b][0], e1[a][1]-e2[b][1])
                        if d<=snap_dist:
                            s1 = polys[i] if a==1 else polys[i][::-1]
                            s2 = polys[j] if b==0 else polys[j][::-1]
                            if d>0.5: s1 = s1+[e2[b]]      # small bridge
                            polys[j]=s1+s2; used[i]=True; changed=True; break
                    if used[i]: break
                if used[i]: break
        polys=[polys[k] for k in range(n) if not used[k]]

    # 2) endpoint → nearest point on other poly (insert vertex; T-join)
    for i in range(len(polys)):
        for end_idx in (0,-1):
            p = polys[i][end_idx]; best=(None,None,1e9,None)
            for j in range(len(polys)):
                if j==i: continue
                for k in range(len(polys[j])-1):
                    q, dist, t = nearest_on_seg(p, polys[j][k], polys[j][k+1])
                    if dist<best[2]: best=(j,k,dist,t)
            j,k,dist,t = best
            if dist<=snap_dist:
                polys[j] = insert_point(polys[j], k, t)
                if end_idx==0: polys[i] = [polys[j][k+1]] + polys[i]
                else:          polys[i] = polys[i] + [polys[j][k+1]]

    # 3) drop stubs
    polys=[p for p in polys if poly_length(p)>=min_len]
    return polys

def remove_parallel_duplicates(polys, parallel_dist=8.0):
    """Remove polylines that run parallel and very close to other polylines."""
    if not polys:
        return polys
    
    def avg_dist_to_poly(p1, p2):
        """Average minimum distance from points on p1 to polyline p2"""
        if len(p1) < 2 or len(p2) < 2:
            return float('inf')
        total_dist = 0
        for pt in p1:
            min_dist = float('inf')
            for k in range(len(p2) - 1):
                _, dist, _ = nearest_on_seg(pt, p2[k], p2[k+1])
                min_dist = min(min_dist, dist)
            total_dist += min_dist
        return total_dist / len(p1)
    
    keep = [True] * len(polys)
    lengths = [poly_length(p) for p in polys]
    indices = sorted(range(len(polys)), key=lambda i: lengths[i], reverse=True)
    
    for i in indices:
        if not keep[i]:
            continue
        for j in indices:
            if i == j or not keep[j]:
                continue
            dist_j_to_i = avg_dist_to_poly(polys[j], polys[i])
            dist_i_to_j = avg_dist_to_poly(polys[i], polys[j])
            avg_dist = (dist_j_to_i + dist_i_to_j) / 2
            if avg_dist < parallel_dist:
                keep[j] = False
    
    return [polys[i] for i in range(len(polys)) if keep[i]]

# ---------- Main ----------
def main():
    ap = argparse.ArgumentParser(description="Red-traced map → simplified blue wall lines")
    ap.add_argument("image", help="Input map image (PNG/JPG)")
    ap.add_argument("--close", type=int, default=5, help="close kernel (px)")
    ap.add_argument("--open",  type=int, default=3, help="open kernel (px)")
    ap.add_argument("--dilate",type=int, default=6, help="skeleton dilation radius (px)")
    ap.add_argument("--eps",   type=float, default=5.0, help="RDP epsilon (px)")
    ap.add_argument("--snap",  type=float, default=6.0, help="snap/bridge distance (px)")
    ap.add_argument("--minlen",type=float, default=12.0, help="min polyline length to keep (px)")
    ap.add_argument("--collinear", type=float, default=0.5, help="collinear tolerance (px) - removes intermediate points on straight lines")
    ap.add_argument("--parallel", type=float, default=0, help="remove parallel duplicate lines closer than this distance (0=disable)")
    ap.add_argument("--outdir", default="out", help="output directory")
    ap.add_argument("--json", action="store_true", help="export polylines as JSON")
    args = ap.parse_args()

    outdir = Path(args.outdir); outdir.mkdir(parents=True, exist_ok=True)
    img = cv2.imread(str(args.image)); H,W = img.shape[:2]
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    # 1) Red mask → clean
    mask = red_mask_hsv(img_rgb); mask = clean_mask(mask, args.close, args.open)
    cv2.imwrite(str(outdir/"mask_debug.png"), mask)

    # 2–3) Dilate → skeleton → polylines
    polylines = skeleton_polylines(mask, args.dilate)

    # 4) Simplify
    polylines = [rdp(p, args.eps) for p in polylines if len(p)>=2]

    # 5–6) Connect & prune
    polylines = connect_polylines(polylines, args.snap, args.minlen)
    points_before_collinear = sum(len(p) for p in polylines)
    
    # 6b) Additional collinear simplification
    if args.collinear > 0:
        polylines = [simplify_collinear(p, args.collinear) for p in polylines]
        polylines = [p for p in polylines if len(p) >= 2]  # Remove any that became too short

    # 6c) Remove parallel duplicates (for thick walls)
    lines_before_parallel = len(polylines)
    points_before_parallel = sum(len(p) for p in polylines)
    if args.parallel > 0:
        polylines = remove_parallel_duplicates(polylines, args.parallel)

    # 7) Save images
    overlay = draw_overlay(img, polylines, color=(255,120,0), thick=2)
    cv2.imwrite(str(outdir/"overlay_blue.png"), overlay)
    cv2.imwrite(str(outdir/"lines_only_transparent.png"),
                lines_only_rgba(polylines, (H,W), thick=2, color_bgr=(255,120,0), white_bg=False))
    cv2.imwrite(str(outdir/"lines_only_white.png"),
                lines_only_rgba(polylines, (H,W), thick=2, color_bgr=(255,120,0), white_bg=True))
    
    # 7b) Save lines + vertices versions (lines with vertex points marked)
    cv2.imwrite(str(outdir/"lines_and_vertices_transparent.png"),
                lines_only_rgba(polylines, (H,W), thick=2, color_bgr=(255,120,0), white_bg=False, lines_and_vertices=True))
    cv2.imwrite(str(outdir/"lines_and_vertices_white.png"),
                lines_only_rgba(polylines, (H,W), thick=2, color_bgr=(255,120,0), white_bg=True, lines_and_vertices=True))

    # 8) (Optional) JSON export
    if args.json:
        data = {"width":W, "height":H, "polylines":[[(float(x),float(y)) for x,y in p] for p in polylines]}
        (outdir/"polylines.json").write_text(json.dumps(data, indent=2))

    # Stats
    npts = sum(len(p) for p in polylines)
    print(f"Done. Polylines={len(polylines)}, points={npts}")
    if args.collinear > 0:
        print(f"Collinear simplification removed {points_before_collinear - npts} points ({points_before_collinear} → {npts})")
    if args.parallel > 0:
        print(f"Parallel duplicate removal: {lines_before_parallel} → {len(polylines)} polylines, {points_before_parallel} → {npts} points")
    print(f"Saved solid lines: {outdir/'overlay_blue.png'}, {outdir/'lines_only_transparent.png'}, {outdir/'lines_only_white.png'}")
    print(f"Saved lines+vertices: {outdir/'lines_and_vertices_transparent.png'}, {outdir/'lines_and_vertices_white.png'}")
    if args.json: print(f"Saved: {outdir/'polylines.json'}")

if __name__ == "__main__":
    main()
