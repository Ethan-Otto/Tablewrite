import './App.css'
import { Header } from './components/Header'
import { ChatWindow } from './components/ChatWindow'
import { InputArea } from './components/InputArea'
import { useChat } from './hooks/useChat'

function App() {
  const { messages, sendMessage, isLoading } = useChat();

  return (
    <div className="min-h-screen bg-[#2d1f15] flex flex-col">
      <Header />
      <ChatWindow messages={messages} />
      <InputArea onSendMessage={sendMessage} disabled={isLoading} />
    </div>
  )
}

export default App
