import { ChatMessage } from '../lib/types';
import { Message } from './Message';

interface ChatWindowProps {
  messages: ChatMessage[];
}

export function ChatWindow({ messages }: ChatWindowProps) {
  return (
    <div className="flex-1 overflow-y-auto bg-[#2d1f15] px-4 py-6">
      <div className="max-w-4xl mx-auto space-y-4">
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <p className="text-[#8d7555] text-lg italic">
              No messages yet. Type a message or use slash commands like /help
            </p>
          </div>
        ) : (
          messages.map((msg, idx) => (
            <Message key={idx} message={msg} />
          ))
        )}
      </div>
    </div>
  );
}
