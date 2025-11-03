export function Header() {
  return (
    <div className="relative px-10 py-6 bg-gradient-to-b from-[#c4b098] to-[#b89d7d] border-4 border-[#8d7555] border-b-2 border-b-[#7d5a3d]">
      {/* Left flourish */}
      <div className="absolute left-32 top-1/2 -translate-y-1/2 text-2xl text-[#7d5a3d]">
        ⚜
      </div>

      {/* Title */}
      <h1 className="text-center text-[#5c3d2e] text-4xl tracking-[0.2em] font-normal drop-shadow-sm">
        Module Assistant
      </h1>

      {/* Right flourish */}
      <div className="absolute right-32 top-1/2 -translate-y-1/2 text-2xl text-[#7d5a3d]">
        ⚜
      </div>
    </div>
  );
}
