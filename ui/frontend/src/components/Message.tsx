import type { ChatMessage } from '../lib/types';
import { ChatRole } from '../lib/types';
import { SceneCard } from './SceneCard';
import ReactMarkdown from 'react-markdown';

interface MessageProps {
  message: ChatMessage;
}

export function Message({ message }: MessageProps) {
  const isUser = message.role === ChatRole.USER;
  const isSystem = message.role === ChatRole.SYSTEM;

  if (isSystem) {
    return (
      <div className="flex justify-center py-2">
        <div className="max-w-md px-4 py-2 text-sm text-[#8d7555] italic text-center">
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className="w-full">
      <div
        className={`flex gap-[15px] ${isUser ? 'flex-row-reverse' : 'flex-row'}`}
        style={{ animation: 'fadeInParchment 0.6s ease-out' }}
      >
        {/* Avatar */}
        <div
          className="flex-shrink-0 w-[50px] h-[50px] rounded-full flex items-center justify-center text-[22px]"
          style={{
            border: '3px double #7d5a3d',
            background: 'radial-gradient(circle, #e8dcc5 0%, #d4c4a8 100%)',
            boxShadow: '0 4px 10px rgba(0, 0, 0, 0.25)'
          }}
        >
          {isUser ? (
            <span style={{ filter: 'grayscale(1) brightness(0)' }}>🧙</span>
          ) : (
            <span>✒</span>
          )}
        </div>

        {/* Message Content */}
        <div
          className="max-w-[70%] rounded-[4px] px-[25px] py-5 relative"
          style={{
            fontFamily: 'IM Fell DW Pica, serif',
            lineHeight: '1.8',
            ...(isUser ? {
              background: 'linear-gradient(135deg, rgba(184, 157, 125, 0.35) 0%, rgba(157, 133, 101, 0.35) 100%)',
              color: '#3d2817',
              border: '2px solid #7d5a3d',
              borderRight: '4px solid #5c3d2e',
              boxShadow: '-4px 4px 0 rgba(125, 90, 61, 0.12), 0 6px 15px rgba(0, 0, 0, 0.18)'
            } : {
              background: 'linear-gradient(135deg, rgba(245, 238, 225, 0.9) 0%, rgba(235, 225, 210, 0.9) 100%)',
              color: '#3d2817',
              border: '2px solid #b89d7d',
              borderLeft: '4px solid #7d5a3d',
              boxShadow: '4px 4px 0 rgba(125, 90, 61, 0.12), 0 6px 15px rgba(0, 0, 0, 0.18)'
            })
          }}
        >
          {/* Message Label */}
          <div
            className="mb-[10px] uppercase tracking-[2px]"
            style={{
              fontFamily: 'Crimson Pro, serif',
              fontSize: '11px',
              fontWeight: 600,
              color: '#7d5a3d',
              letterSpacing: '2px'
            }}
          >
            {isUser ? 'YOU' : 'ASSISTANT'}
          </div>

          {/* Message Text */}
          <div className="prose prose-sm max-w-none prose-p:my-2 prose-headings:font-serif prose-headings:text-[#3d2817] prose-strong:text-[#3d2817] prose-strong:font-semibold prose-code:text-sm prose-code:font-normal prose-code:bg-[rgba(125,90,61,0.1)] prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-code:before:content-none prose-code:after:content-none text-left">
            <ReactMarkdown>{message.content}</ReactMarkdown>
          </div>
        </div>
      </div>

      {/* Render Scene Card if scene data is present */}
      {message.scene && (
        <div className="mt-4">
          <SceneCard scene={message.scene} />
        </div>
      )}

      <style>{`
        @keyframes fadeInParchment {
          from {
            opacity: 0;
            transform: translateY(10px) scale(0.98);
          }
          to {
            opacity: 1;
            transform: translateY(0) scale(1);
          }
        }
      `}</style>
    </div>
  );
}
