import { ChatMessage, ChatRole } from '../lib/types';

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
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} py-2 px-4`}>
      <div
        className={`max-w-[70%] rounded-lg px-4 py-3 shadow-md ${
          isUser
            ? 'bg-gradient-to-br from-[#d4c4a8] to-[#c4b098] border-2 border-[#a89d7d]'
            : 'bg-gradient-to-br from-[#e8dcc5] to-[#d8cbb5] border-2 border-[#b8ad8d]'
        }`}
      >
        {!isUser && (
          <div className="flex items-center gap-2 mb-2 pb-2 border-b border-[#b8ad8d]">
            <span className="text-lg">✒</span>
            <span className="text-sm font-semibold text-[#5c3d2e]">Assistant</span>
          </div>
        )}
        <div className="text-[#3d2817] whitespace-pre-wrap leading-relaxed">
          {message.content}
        </div>
      </div>
    </div>
  );
}
