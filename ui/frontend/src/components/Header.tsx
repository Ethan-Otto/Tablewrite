export function Header() {
  return (
    <div
      className="relative px-10 py-3 border-b-0"
      style={{
        background: 'linear-gradient(180deg, rgba(92, 61, 46, 0.15) 0%, transparent 100%), linear-gradient(180deg, #b89d7d 0%, #9d8565 100%)',
        border: '4px double #7d5a3d',
        borderBottom: 'none',
        boxShadow: 'inset 0 2px 10px rgba(0, 0, 0, 0.15)'
      }}
    >
      {/* Left flourish */}
      <div className="absolute left-32 top-1/2 -translate-y-1/2 text-[28px] text-[#7d5a3d]">
        ❦
      </div>

      {/* Title */}
      <h1
        className="text-center text-[#5c3d2e] text-[36px] tracking-[3px] font-normal m-0"
        style={{
          fontFamily: 'UnifrakturMaguntia, cursive',
          textShadow: '2px 2px 0 rgba(255, 255, 255, 0.2)'
        }}
      >
        Module Assistant
      </h1>

      {/* Right flourish */}
      <div className="absolute right-32 top-1/2 -translate-y-1/2 text-[28px] text-[#7d5a3d]">
        ❦
      </div>
    </div>
  );
}
