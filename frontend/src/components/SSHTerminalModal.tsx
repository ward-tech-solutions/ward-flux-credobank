import { useState } from 'react'
import { Modal, ModalHeader, ModalTitle, ModalContent } from '@/components/ui/Modal'
import Button from '@/components/ui/Button'
import Input from '@/components/ui/Input'
import { Terminal, Plug, AlertTriangle } from 'lucide-react'
import { sshAPI } from '@/services/api'

interface SSHTerminalModalProps {
  open: boolean
  onClose: () => void
  deviceName: string
  deviceIP: string
}

export default function SSHTerminalModal({ open, onClose, deviceName, deviceIP }: SSHTerminalModalProps) {
  const [username, setUsername] = useState('admin')
  const [password, setPassword] = useState('')
  const [output, setOutput] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isConnecting, setIsConnecting] = useState(false)
  const [isConnected, setIsConnected] = useState(false)

  const handleConnect = async () => {
    if (!password) {
      setError('Please enter a password')
      return
    }

    setIsConnecting(true)
    setError(null)
    setOutput(null)

    try {
      const response = await sshAPI.connect({
        host: deviceIP,
        username,
        password,
        port: 22,
      })

      if (response.data.success) {
        setIsConnected(true)
        setOutput(response.data.output || 'Connection established. SSH terminal access via CLI is recommended for full interactive experience.')
      } else {
        setError(response.data.error || 'Failed to connect')
      }
    } catch (err: any) {
      const errorMsg = err.response?.data?.error || err.message || 'Failed to connect. Please check credentials and network connectivity.'
      setError(errorMsg)
    } finally {
      setIsConnecting(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !isConnecting) {
      handleConnect()
    }
  }

  const handleClose = () => {
    setUsername('admin')
    setPassword('')
    setOutput(null)
    setError(null)
    setIsConnected(false)
    setIsConnecting(false)
    onClose()
  }

  return (
    <Modal open={open} onClose={handleClose} size="lg">
      <ModalHeader onClose={handleClose}>
        <ModalTitle className="flex items-center gap-2">
          <Terminal className="h-6 w-6 text-ward-green" />
          SSH Terminal - {deviceName} ({deviceIP})
        </ModalTitle>
      </ModalHeader>
      <ModalContent className="p-0">
        {/* Terminal Output */}
        <div className="h-96 bg-gray-900 text-green-400 font-mono text-sm overflow-y-auto p-4">
          {!output && !error && (
            <div className="flex flex-col items-center justify-center h-full text-gray-500">
              <Terminal className="h-16 w-16 mb-4" />
              <p>Enter credentials below and click Connect to access the device terminal</p>
            </div>
          )}
          {output && (
            <pre className="whitespace-pre-wrap">
              {`Connected to ${deviceIP}

${output}

To use full SSH terminal features, use your preferred SSH client:
ssh ${username}@${deviceIP}
`}
            </pre>
          )}
          {error && (
            <div className="flex items-start gap-3 text-red-400">
              <AlertTriangle className="h-5 w-5 mt-0.5 flex-shrink-0" />
              <div>
                <p className="font-semibold">Connection Failed</p>
                <p className="mt-1">{error}</p>
              </div>
            </div>
          )}
        </div>

        {/* Credentials Form */}
        <div className="p-4 bg-gray-100 border-t border-gray-300">
          <div className="flex items-center gap-3">
            <Input
              type="text"
              placeholder="Username (default: admin)"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              disabled={isConnecting || isConnected}
              className="flex-1"
            />
            <Input
              type="password"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              onKeyPress={handleKeyPress}
              disabled={isConnecting || isConnected}
              className="flex-1"
            />
            <Button
              onClick={handleConnect}
              disabled={isConnecting || isConnected}
              className="bg-ward-green hover:bg-ward-green/90"
            >
              {isConnecting ? (
                <>
                  <div className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full mr-2" />
                  Connecting...
                </>
              ) : isConnected ? (
                <>
                  <Plug className="h-4 w-4 mr-2" />
                  Connected
                </>
              ) : (
                <>
                  <Plug className="h-4 w-4 mr-2" />
                  Connect
                </>
              )}
            </Button>
          </div>
          <p className="text-xs text-gray-600 mt-2">
            <AlertTriangle className="h-3 w-3 inline mr-1" />
            Enter credentials and click Connect to access the device terminal
          </p>
        </div>
      </ModalContent>
    </Modal>
  )
}
