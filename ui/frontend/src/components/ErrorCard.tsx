interface ErrorCardProps {
  message: string;
}

export function ErrorCard({ message }: ErrorCardProps) {
  return (
    <div
      className="mt-4 max-w-[600px] rounded px-4 py-3"
      style={{
        background: 'rgba(139, 31, 31, 0.1)',
        border: '2px solid #8b1f1f',
        borderRadius: '4px',
        fontFamily: 'IM Fell DW Pica, serif',
        color: '#5c1515'
      }}
    >
      <div className="flex items-start gap-2">
        <span style={{ fontSize: '18px' }}>⚠</span>
        <div>{message}</div>
      </div>
    </div>
  );
}
