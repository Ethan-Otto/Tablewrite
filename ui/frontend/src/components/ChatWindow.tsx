import { useEffect, useRef } from 'react';
import type { ChatMessage } from '../lib/types';
import { Message } from './Message';

interface ChatWindowProps {
  messages: ChatMessage[];
}

export function ChatWindow({ messages }: ChatWindowProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div
      className="flex-1 overflow-y-auto px-10 pt-2 pb-2 relative"
      style={{
        background: `
          repeating-linear-gradient(0deg, transparent 0px, rgba(125, 90, 61, 0.02) 1px, transparent 2px, transparent 20px),
          repeating-linear-gradient(90deg, transparent 0px, rgba(125, 90, 61, 0.02) 1px, transparent 2px, transparent 20px),
          radial-gradient(circle at 30% 30%, rgba(240, 230, 210, 1) 0%, rgba(230, 218, 195, 1) 100%)
        `,
        borderLeft: '4px double #7d5a3d',
        borderRight: '4px double #7d5a3d',
        boxShadow: 'inset 0 0 100px rgba(125, 90, 61, 0.06)'
      }}
    >
      {/* Aging spots overlay */}
      <div
        className="absolute top-0 left-0 right-0 bottom-0 pointer-events-none"
        style={{
          backgroundImage: `
            radial-gradient(circle at 15% 25%, rgba(139, 90, 43, 0.08) 0%, transparent 4%),
            radial-gradient(circle at 82% 45%, rgba(139, 90, 43, 0.06) 0%, transparent 3%),
            radial-gradient(circle at 45% 78%, rgba(139, 90, 43, 0.07) 0%, transparent 5%),
            radial-gradient(circle at 68% 12%, rgba(139, 90, 43, 0.05) 0%, transparent 3%)
          `
        }}
      />

      <div className="relative space-y-[30px]">
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <p className="text-[#8d7555] text-lg italic">
              No messages yet. Type a message or use slash commands like /help
            </p>
          </div>
        ) : (
          <>
            {messages.map((msg, idx) => (
              <Message key={idx} message={msg} />
            ))}
            {/* Invisible element at the bottom to scroll to */}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      <style>{`
        .flex-1::-webkit-scrollbar {
          width: 12px;
        }
        .flex-1::-webkit-scrollbar-track {
          background: rgba(184, 157, 125, 0.3);
          border: 1px solid #b89d7d;
        }
        .flex-1::-webkit-scrollbar-thumb {
          background: linear-gradient(180deg, #7d5a3d 0%, #5c3d2e 100%);
          border-radius: 6px;
          border: 2px solid #e8dcc5;
        }
        .flex-1::-webkit-scrollbar-thumb:hover {
          background: linear-gradient(180deg, #8d6a4d 0%, #6d4d3e 100%);
        }
      `}</style>
    </div>
  );
}
