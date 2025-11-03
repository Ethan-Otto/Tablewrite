import './App.css'
import { useState } from 'react'
import { Header } from './components/Header'
import { ChatWindow } from './components/ChatWindow'
import { InputArea } from './components/InputArea'
import { ChatMessage, ChatRole } from './lib/types'

// Initial welcome message
const initialMessages: ChatMessage[] = [
  {
    role: ChatRole.SYSTEM,
    content: 'Welcome to the D&D Module Assistant',
    timestamp: new Date().toISOString()
  }
];

function App() {
  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages);

  const handleSendMessage = (content: string) => {
    const newMessage: ChatMessage = {
      role: ChatRole.USER,
      content,
      timestamp: new Date().toISOString()
    };
    setMessages(prev => [...prev, newMessage]);

    // TODO: Send to backend and get response (Task 11)
    // For now, just add a placeholder assistant response
    setTimeout(() => {
      const response: ChatMessage = {
        role: ChatRole.ASSISTANT,
        content: `You sent: "${content}"\n\nBackend integration coming in Task 11!`,
        timestamp: new Date().toISOString()
      };
      setMessages(prev => [...prev, response]);
    }, 500);
  };

  return (
    <div className="min-h-screen bg-[#2d1f15] flex flex-col">
      <Header />
      <ChatWindow messages={messages} />
      <InputArea onSendMessage={handleSendMessage} />
    </div>
  )
}

export default App
