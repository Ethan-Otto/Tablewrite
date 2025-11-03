import { Scene } from '../lib/types';

interface SceneCardProps {
  scene: Scene;
}

export function SceneCard({ scene }: SceneCardProps) {
  return (
    <div className="my-4 mx-auto max-w-2xl rounded-lg border-4 border-[#8d7555] bg-gradient-to-br from-[#e8dcc5] to-[#d8cbb5] overflow-hidden shadow-lg">
      {/* Scene Image (if available) */}
      {scene.image_url && (
        <div className="w-full h-64 bg-[#3d2817] flex items-center justify-center">
          <img 
            src={scene.image_url} 
            alt={scene.name}
            className="w-full h-full object-cover"
          />
        </div>
      )}

      {/* Scene Content */}
      <div className="p-6">
        {/* Scene Name */}
        <div className="flex items-center gap-3 mb-4">
          <span className="text-2xl">🗺</span>
          <h3 className="text-2xl text-[#3d2817] font-heading tracking-wide">
            {scene.name}
          </h3>
        </div>

        {/* Location Type Badge */}
        {scene.location_type && (
          <div className="inline-block px-3 py-1 mb-3 rounded-full bg-[#a89d7d] text-[#3d2817] text-sm font-semibold">
            {scene.location_type}
          </div>
        )}

        {/* Scene Description */}
        <div className="text-[#3d2817] leading-relaxed whitespace-pre-wrap mb-4">
          {scene.description}
        </div>

        {/* Section Path */}
        {scene.section_path && (
          <div className="text-sm text-[#8d7555] italic border-t border-[#b8ad8d] pt-3">
            <span className="font-semibold">Location: </span>
            {scene.section_path}
          </div>
        )}
      </div>
    </div>
  );
}
