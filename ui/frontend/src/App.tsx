import './App.css'
import { Header } from './components/Header'
import { ChatWindow } from './components/ChatWindow'
import { InputArea } from './components/InputArea'
import { useChat } from './hooks/useChat'

function App() {
  const { messages, sendMessage, isLoading } = useChat();

  return (
    <div className="h-screen overflow-hidden flex justify-center px-3 pb-10" style={{
      background: 'linear-gradient(135deg, #d4c4a8 0%, #c4b098 50%, #d4c4a8 100%)'
    }}>
      <div className="w-full max-w-[1000px] flex flex-col h-full" style={{
        boxShadow: '0 30px 60px rgba(0, 0, 0, 0.4), inset 0 0 100px rgba(0, 0, 0, 0.05)'
      }}>
        <Header />
        <ChatWindow messages={messages} />
        <InputArea onSendMessage={sendMessage} disabled={isLoading} />
      </div>
    </div>
  )
}

export default App
