import { useState } from 'react';
import type { ImageData } from '../lib/types';

interface ImageCarouselProps {
  data: ImageData;
}

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export function ImageCarousel({ data }: ImageCarouselProps) {
  console.log('[DEBUG] ImageCarousel rendering with data:', data);
  const [currentIndex, setCurrentIndex] = useState(0);

  // Convert relative URLs to absolute URLs
  const imageUrls = data.image_urls.map(url =>
    url.startsWith('http') ? url : `${API_BASE_URL}${url}`
  );

  const nextImage = () => {
    setCurrentIndex((prev) => (prev + 1) % imageUrls.length);
  };

  const prevImage = () => {
    setCurrentIndex((prev) =>
      prev === 0 ? imageUrls.length - 1 : prev - 1
    );
  };

  return (
    <div
      className="mt-4 max-w-[600px]"
      style={{
        border: '4px double #7d5a3d',
        borderRadius: '4px',
        background: 'linear-gradient(135deg, #f5eee1 0%, #ebe1d2 100%)',
        padding: '16px'
      }}
    >
      {/* Image display */}
      <div className="relative">
        <img
          src={imageUrls[currentIndex]}
          alt={data.prompt}
          className="w-full h-auto rounded"
          style={{
            boxShadow: '0 4px 10px rgba(0, 0, 0, 0.15)'
          }}
        />

        {/* Navigation arrows (only show if multiple images) */}
        {imageUrls.length > 1 && (
          <>
            <button
              onClick={prevImage}
              className="absolute left-2 top-1/2 -translate-y-1/2 w-10 h-10 rounded-full flex items-center justify-center transition-all"
              style={{
                background: 'radial-gradient(circle, #8b1f1f 0%, #6d1818 100%)',
                border: '2px solid #5c1515',
                color: '#f5eee1',
                fontSize: '20px',
                cursor: 'pointer',
                boxShadow: '0 4px 10px rgba(0, 0, 0, 0.3)'
              }}
              onMouseEnter={(e) => e.currentTarget.style.opacity = '0.9'}
              onMouseLeave={(e) => e.currentTarget.style.opacity = '1'}
              onMouseDown={(e) => e.currentTarget.style.transform = 'translateY(-50%) translateY(1px)'}
              onMouseUp={(e) => e.currentTarget.style.transform = 'translateY(-50%)'}
            >
              ◀
            </button>
            <button
              onClick={nextImage}
              className="absolute right-2 top-1/2 -translate-y-1/2 w-10 h-10 rounded-full flex items-center justify-center transition-all"
              style={{
                background: 'radial-gradient(circle, #8b1f1f 0%, #6d1818 100%)',
                border: '2px solid #5c1515',
                color: '#f5eee1',
                fontSize: '20px',
                cursor: 'pointer',
                boxShadow: '0 4px 10px rgba(0, 0, 0, 0.3)'
              }}
              onMouseEnter={(e) => e.currentTarget.style.opacity = '0.9'}
              onMouseLeave={(e) => e.currentTarget.style.opacity = '1'}
              onMouseDown={(e) => e.currentTarget.style.transform = 'translateY(-50%) translateY(1px)'}
              onMouseUp={(e) => e.currentTarget.style.transform = 'translateY(-50%)'}
            >
              ▶
            </button>
          </>
        )}
      </div>

      {/* Image counter */}
      {imageUrls.length > 1 && (
        <div
          className="text-center mt-3"
          style={{
            fontFamily: 'Crimson Pro, serif',
            fontSize: '14px',
            color: '#7d5a3d',
            fontWeight: 600
          }}
        >
          {currentIndex + 1} / {imageUrls.length}
        </div>
      )}
    </div>
  );
}
