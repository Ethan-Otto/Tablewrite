import { useState, KeyboardEvent } from 'react';

interface InputAreaProps {
  onSendMessage: (message: string) => void;
  disabled?: boolean;
}

export function InputArea({ onSendMessage, disabled = false }: InputAreaProps) {
  const [message, setMessage] = useState('');

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
    <div className="border-t-4 border-[#8d7555] bg-gradient-to-b from-[#c4b098] to-[#b89d7d] px-6 py-6">
      <div className="max-w-4xl mx-auto flex gap-4 items-end">
        {/* Text Input */}
        <div className="flex-1">
          <textarea
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            placeholder="Type a message or use /help for commands..."
            className="w-full px-4 py-3 rounded-lg bg-[#e8dcc5] border-2 border-[#a89d7d] 
                     text-[#3d2817] placeholder-[#8d7555] resize-none
                     focus:outline-none focus:ring-2 focus:ring-[#7d5a3d] focus:border-transparent
                     disabled:opacity-50 disabled:cursor-not-allowed
                     font-ui"
            rows={2}
          />
        </div>

        {/* Wax Seal Button */}
        <button
          onClick={handleSend}
          disabled={disabled || !message.trim()}
          className="relative group disabled:opacity-50 disabled:cursor-not-allowed"
          aria-label="Send message"
        >
          {/* Wax seal base */}
          <div className="relative w-16 h-16 rounded-full bg-gradient-radial from-[#a62828] via-[#8b1f1f] to-[#6b1515] 
                        shadow-lg border-2 border-[#6b1515]
                        transition-all duration-200
                        group-hover:shadow-xl group-hover:scale-105 group-active:scale-95
                        disabled:group-hover:scale-100">
            {/* Fleur-de-lis symbol */}
            <div className="absolute inset-0 flex items-center justify-center text-[#d4c4a8] text-2xl font-bold">
              ⚜
            </div>
            
            {/* Wax texture overlay */}
            <div className="absolute inset-0 rounded-full bg-[url('data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI1IiBoZWlnaHQ9IjUiPgo8cmVjdCB3aWR0aD0iNSIgaGVpZ2h0PSI1IiBmaWxsPSIjZmZmIj48L3JlY3Q+CjxwYXRoIGQ9Ik0wIDVMNSAwWk02IDRMNCA2Wk0tMSAxTDEgLTFaIiBzdHJva2U9IiM4ODgiIHN0cm9rZS13aWR0aD0iMSI+PC9wYXRoPgo8L3N2Zz4=')] opacity-10">
            </div>
          </div>
        </button>
      </div>
      
      {/* Helper text */}
      <div className="max-w-4xl mx-auto mt-2 text-xs text-[#7d5a3d] text-center">
        Press Enter to send • Shift+Enter for new line
      </div>
    </div>
  );
}
