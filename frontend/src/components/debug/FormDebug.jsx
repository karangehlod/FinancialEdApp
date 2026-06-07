// FRONTEND FORM SUBMISSION DEBUG COMPONENT
// This file helps diagnose why the form is not submitting

import React, { useState } from 'react'

export const FormDebug = () => {
  const [testForm, setTestForm] = useState({
    name: '',
    email: '',
  })
  const [logs, setLogs] = useState([])

  const addLog = (message) => {
    if (import.meta.env.DEV) {
      console.log('[FORM-DEBUG]', message)
    }
    setLogs((prev) => [...prev, `[${new Date().toLocaleTimeString()}] ${message}`])
  }

  const handleSubmit = async (e) => {
    addLog('✅ handleSubmit called')
    e.preventDefault()
    addLog('✅ e.preventDefault() called')

    addLog('📤 Making API call...')
    try {
      const response = await fetch('http://localhost:8000/api/v1/auth/me', {
        method: 'GET',
        headers: {
          'Authorization': 'Bearer test-token',
          'Content-Type': 'application/json',
        },
      })
      addLog(`📬 Response received: ${response.status}`)
      const data = await response.json()
      addLog(`✅ Response data: ${JSON.stringify(data).substring(0, 100)}`)
    } catch (error) {
      addLog(`❌ Error: ${error.message}`)
    }
  }

  return (
    <div className="p-8 bg-white rounded-lg">
      <h2 className="text-2xl font-bold mb-4">Form Submission Debug</h2>
      
      <form onSubmit={handleSubmit} className="space-y-4 mb-8">
        <input
          type="text"
          value={testForm.name}
          onChange={(e) => {
            addLog(`Input changed: ${e.target.value}`)
            setTestForm({ ...testForm, name: e.target.value })
          }}
          placeholder="Enter name"
          className="w-full px-4 py-2 border rounded"
        />
        <button
          type="submit"
          className="px-4 py-2 bg-blue-500 text-white rounded"
          onClick={() => addLog('🖱️ Button clicked')}
        >
          Submit Form
        </button>
      </form>

      <div className="bg-gray-100 p-4 rounded">
        <h3 className="font-bold mb-2">Debug Logs:</h3>
        <div className="space-y-1 font-mono text-sm">
          {logs.map((log, i) => (
            <div key={i} className="text-gray-700">
              {log}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
