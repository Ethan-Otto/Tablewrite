import { useState, KeyboardEvent } from 'react';

interface InputAreaProps {
  onSendMessage: (message: string) => void;
  disabled?: boolean;
}

export function InputArea({ onSendMessage, disabled = false }: InputAreaProps) {
  const [message, setMessage] = useState('');
  const [isPressed, setIsPressed] = useState(false);

  const handleSend = () => {
    if (message.trim() && !disabled) {
      onSendMessage(message);
      setMessage('');
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div
      className="px-10 pt-[25px] pb-3"
      style={{
        background: 'linear-gradient(180deg, #b89d7d 0%, #9d8565 100%)',
        border: '4px double #7d5a3d',
        borderTop: 'none'
      }}
    >
      <div className="flex gap-[15px] items-center">
        {/* Text Input */}
        <textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          placeholder="/generate-scene [description]"
          className="flex-1 px-6 py-4 rounded-[4px] resize-none outline-none transition-all duration-300"
          style={{
            background: 'rgba(245, 238, 225, 0.95)',
            border: '2px solid #7d5a3d',
            fontFamily: 'IM Fell DW Pica, serif',
            fontSize: '16px',
            color: '#3d2817',
            boxShadow: 'inset 2px 2px 5px rgba(0, 0, 0, 0.12)'
          }}
          rows={2}
        />

        {/* Wax Seal Button with Ribbon */}
        <div className="relative flex-shrink-0" style={{ position: 'relative' }}>
          {/* Ribbon underneath seal */}
          <div
            style={{
              content: '""',
              position: 'absolute',
              bottom: '12px',
              left: '50%',
              transform: 'translateX(-50%)',
              width: '45px',
              height: '70px',
              background: 'linear-gradient(180deg, #5c3d2e 0%, #4a3020 100%)',
              clipPath: 'polygon(0 0, 100% 0, 100% 85%, 50% 100%, 0 85%)',
              boxShadow: '0 2px 6px rgba(0, 0, 0, 0.3)',
              zIndex: 0
            }}
          />

          {/* Wax Seal Button */}
          <button
            onClick={handleSend}
            onMouseDown={() => setIsPressed(true)}
            onMouseUp={() => setIsPressed(false)}
            onMouseLeave={() => setIsPressed(false)}
            disabled={disabled || !message.trim()}
            className="relative cursor-pointer transition-all duration-200 flex-shrink-0 flex items-center justify-center overflow-visible"
            style={{
              width: '78px',
              height: '78px',
              background: 'radial-gradient(circle at 35% 30%, #a83030 0%, #9d2424 20%, #8b1f1f 40%, #721818 70%, #5a1212 100%)',
              border: 'none',
              borderRadius: '44% 56% 48% 52% / 53% 47% 53% 47%',
              boxShadow: '0 1px 3px rgba(0, 0, 0, 0.4)',
              zIndex: 1
            }}
            aria-label="Send message"
          >
            {/* Embossed ring */}
            <div
              style={{
                position: 'absolute',
                width: '56px',
                height: '56px',
                borderRadius: '50%',
                border: '2px solid rgba(0, 0, 0, 0.3)',
                boxShadow: 'inset 0 0 6px rgba(0, 0, 0, 0.35)',
                zIndex: 1
              }}
            />

            {/* Inner shadow when pressed */}
            {isPressed && (
              <div
                style={{
                  position: 'absolute',
                  width: '56px',
                  height: '56px',
                  borderRadius: '50%',
                  background: 'radial-gradient(circle at center, rgba(0, 0, 0, 0.5) 0%, rgba(0, 0, 0, 0.3) 40%, transparent 70%)',
                  zIndex: 2,
                  pointerEvents: 'none'
                }}
              />
            )}

            {/* Central emblem */}
            <span
              className="seal-emblem"
              style={{
                fontFamily: 'UnifrakturMaguntia, cursive',
                fontSize: '44px',
                color: 'rgba(0, 0, 0, 0.4)',
                textShadow: '0 1px 1px rgba(0, 0, 0, 0.5)',
                zIndex: 2,
                position: 'relative'
              }}
            >
              ⚜
            </span>

            {/* Wax texture overlay */}
            <div
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                borderRadius: '44% 56% 48% 52% / 53% 47% 53% 47%',
                backgroundImage: `
                  radial-gradient(circle at 15% 20%, rgba(0, 0, 0, 0.18) 1.5px, transparent 1.5px),
                  radial-gradient(circle at 85% 30%, rgba(0, 0, 0, 0.15) 1.5px, transparent 1.5px),
                  radial-gradient(circle at 60% 75%, rgba(0, 0, 0, 0.12) 1px, transparent 1px),
                  radial-gradient(circle at 30% 80%, rgba(0, 0, 0, 0.16) 1px, transparent 1px),
                  radial-gradient(circle at 70% 15%, rgba(168, 48, 48, 0.25) 2px, transparent 2px),
                  radial-gradient(circle at 45% 45%, rgba(0, 0, 0, 0.08) 1px, transparent 1px)
                `,
                backgroundSize: '20px 20px, 25px 25px, 18px 18px, 23px 23px, 30px 30px, 15px 15px',
                pointerEvents: 'none',
                opacity: 0.8
              }}
            />

            {/* Wax drip */}
            <div
              style={{
                position: 'absolute',
                bottom: '-10px',
                left: '50%',
                transform: 'translateX(-50%)',
                width: '18px',
                height: '14px',
                background: 'radial-gradient(circle at 40% 20%, #8b1f1f 0%, #5a1212 100%)',
                borderRadius: '0 0 45% 55%',
                boxShadow: '0 2px 5px rgba(0, 0, 0, 0.4)'
              }}
            />

            {/* Wax crack */}
            <div
              style={{
                position: 'absolute',
                top: '22%',
                right: '18%',
                width: '12px',
                height: '1.5px',
                background: 'rgba(0, 0, 0, 0.25)',
                transform: 'rotate(-25deg)',
                borderRadius: '50%'
              }}
            />
          </button>
        </div>
      </div>

      {/* Helper text */}
      <div
        className="mt-2 mb-0 text-center italic"
        style={{
          fontFamily: 'IM Fell DW Pica, serif',
          fontSize: '13px',
          color: '#5c3d2e'
        }}
      >
        Press Enter to send • Shift+Enter for new line
      </div>

      <style>{`
        .command-input::placeholder {
          color: #9d8565;
          font-style: italic;
        }
        .command-input:focus {
          border-color: #5c3d2e;
          box-shadow: 0 0 0 3px rgba(125, 90, 61, 0.25), inset 2px 2px 5px rgba(0, 0, 0, 0.12);
        }
        button:hover:not(:disabled) {
          opacity: 0.95;
        }
        button:active:not(:disabled) {
          opacity: 0.9;
          transform: scale(0.98);
        }
      `}</style>
    </div>
  );
}
