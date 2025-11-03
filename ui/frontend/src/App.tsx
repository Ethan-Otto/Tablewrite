import { useState, useEffect } from 'react'
import reactLogo from './assets/react.svg'
import viteLogo from '/vite.svg'
import './App.css'
import { api } from './lib/api'

function App() {
  const [count, setCount] = useState(0)
  const [healthStatus, setHealthStatus] = useState<string>('checking...')

  useEffect(() => {
    api.health()
      .then(response => {
        console.log('Health check response:', response)
        setHealthStatus(`${response.status} - ${response.service}`)
      })
      .catch(error => {
        console.error('Health check error:', error)
        setHealthStatus('error - backend not running')
      })
  }, [])

  return (
    <>
      <div>
        <a href="https://vite.dev" target="_blank">
          <img src={viteLogo} className="logo" alt="Vite logo" />
        </a>
        <a href="https://react.dev" target="_blank">
          <img src={reactLogo} className="logo react" alt="React logo" />
        </a>
      </div>
      <h1>Vite + React</h1>
      <div className="card">
        <p>API Health: {healthStatus}</p>
        <button onClick={() => setCount((count) => count + 1)}>
          count is {count}
        </button>
        <p>
          Edit <code>src/App.tsx</code> and save to test HMR
        </p>
      </div>
      <p className="read-the-docs">
        Click on the Vite and React logos to learn more
      </p>
    </>
  )
}

export default App
