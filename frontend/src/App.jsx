import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { useEffect, useState } from 'react'
import TopBar from './components/TopBar'
import ErrorToast from './components/ErrorToast'
import HomePage from './pages/HomePage'
import DashboardPage from './pages/DashboardPage'
import { fetchDashboardOverview } from './api/index'

export default function App() {
  const [globalData, setGlobalData] = useState(null)

  useEffect(() => {
    fetchDashboardOverview()
      .then(setGlobalData)
      .catch(console.error)
  }, [])

  return (
    <BrowserRouter>
      <div
        className="flex flex-col"
        style={{ height: '100vh', background: '#0d0f14', overflow: 'hidden' }}
      >
        <TopBar globalData={globalData} />
        <div className="flex-1 overflow-hidden flex flex-col">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/dashboard" element={<DashboardPage />} />
          </Routes>
        </div>
        <ErrorToast />
      </div>
    </BrowserRouter>
  )
}
