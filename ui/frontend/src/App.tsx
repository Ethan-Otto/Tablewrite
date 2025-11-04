import './App.css'
import { Header } from './components/Header'
import { ChatWindow } from './components/ChatWindow'
import { InputArea } from './components/InputArea'
import { useChat } from './hooks/useChat'

function App() {
  const { messages, sendMessage, isLoading } = useChat();

  return (
    <div className="h-screen px-3" style={{
      background: 'linear-gradient(135deg, #d4c4a8 0%, #c4b098 50%, #d4c4a8 100%)',
      position: 'absolute',
      top: '0',
      left: '0',
      right: '0',
      bottom: '0'
    }}>
      <div className="w-full max-w-[1000px] flex flex-col mx-auto mb-0" style={{
        height: 'calc(100vh - 40px)',
        boxShadow: '0 30px 60px rgba(0, 0, 0, 0.4), inset 0 0 100px rgba(0, 0, 0, 0.05)',
        border: '4px double #7d5a3d',
        borderTop: 'none'
      }}>
        <Header />
        <ChatWindow messages={messages} />
        <InputArea onSendMessage={sendMessage} disabled={isLoading} />
      </div>
    </div>
  )
}

export default App
