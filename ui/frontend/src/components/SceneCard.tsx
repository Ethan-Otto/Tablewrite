import type { Scene } from '../lib/types';

interface SceneCardProps {
  scene: Scene;
}

export function SceneCard({ scene }: SceneCardProps) {
  return (
    <div
      className="my-[30px] mx-0 rounded-lg p-[30px] relative"
      style={{
        background: 'linear-gradient(135deg, rgba(245, 238, 225, 0.95) 0%, rgba(235, 225, 210, 0.95) 100%)',
        border: '3px double #7d5a3d',
        borderRadius: '8px',
        boxShadow: '6px 6px 0 rgba(125, 90, 61, 0.18), 0 10px 30px rgba(0, 0, 0, 0.25)'
      }}
    >
      {/* Decorative flourish above card */}
      <div
        style={{
          position: 'absolute',
          top: '-20px',
          left: '50%',
          transform: 'translateX(-50%)',
          fontSize: '40px',
          color: '#7d5a3d',
          background: 'linear-gradient(135deg, #e8dcc5 0%, #d4c4a8 100%)',
          padding: '0 20px'
        }}
      >
        ❦
      </div>

      {/* Scene Title */}
      <h3
        className="text-center mb-5 mt-[10px] pb-[15px]"
        style={{
          fontFamily: 'UnifrakturMaguntia, cursive',
          color: '#5c3d2e',
          fontSize: '28px',
          letterSpacing: '2px',
          borderBottom: '2px double #7d5a3d'
        }}
      >
        {scene.name}
      </h3>

      {/* Scene Image (if available) */}
      {scene.image_url && (
        <div
          className="w-full mb-5 rounded flex items-center justify-center"
          style={{
            height: '280px',
            background: `
              repeating-linear-gradient(45deg, #c4b098 0px, #c4b098 2px, #b89d7d 2px, #b89d7d 4px),
              linear-gradient(135deg, #d4c4a8 0%, #c4b098 100%)
            `,
            border: '3px double #7d5a3d',
            borderRadius: '4px',
            color: '#7d5a3d',
            fontStyle: 'italic',
            boxShadow: 'inset 0 0 50px rgba(0, 0, 0, 0.12)'
          }}
        >
          <img
            src={scene.image_url}
            alt={scene.name}
            className="w-full h-full object-cover rounded"
          />
        </div>
      )}

      {/* Scene Description */}
      <div
        className="whitespace-pre-wrap text-justify"
        style={{
          color: '#3d2817',
          lineHeight: '1.9',
          fontSize: '17px',
          fontFamily: 'IM Fell DW Pica, serif'
        }}
      >
        {scene.description}
      </div>

      {/* Location Type Badge */}
      {scene.location_type && (
        <div
          className="inline-block px-3 py-1 mt-4 rounded-full text-sm font-semibold"
          style={{
            background: '#a89d7d',
            color: '#3d2817'
          }}
        >
          {scene.location_type}
        </div>
      )}

      {/* Section Path */}
      {scene.section_path && (
        <div
          className="text-sm italic border-t pt-3 mt-4"
          style={{
            color: '#8d7555',
            borderColor: '#b8ad8d'
          }}
        >
          <span className="font-semibold">Location: </span>
          {scene.section_path}
        </div>
      )}
    </div>
  );
}
