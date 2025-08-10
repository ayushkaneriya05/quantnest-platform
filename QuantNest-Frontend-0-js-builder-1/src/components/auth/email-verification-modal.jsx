import { useState } from 'react'
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Mail, CheckCircle } from 'lucide-react'
import api from '@/services/api'

export default function EmailVerificationModal({ isOpen, onClose, email }) {
  const [isResending, setIsResending] = useState(false)
  const [resendMessage, setResendMessage] = useState('')
  const [resendError, setResendError] = useState('')

  const handleResendEmail = async () => {
    setIsResending(true)
    setResendMessage('')
    setResendError('')

    try {
      await api.post('users/auth/registration/resend-email/', { email })
      setResendMessage('Verification email sent successfully! Please check your inbox.')
    } catch (err) {
      setResendError(err.response?.data?.detail || 'Failed to resend verification email.')
    } finally {
      setIsResending(false)
    }
  }

  const handleClose = () => {
    setResendMessage('')
    setResendError('')
    onClose()
  }

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[425px] bg-gray-900/50 border border-gray-800/50 text-slate-100 rounded-xl p-6">
        <DialogHeader className="text-center">
          <div className="flex justify-center mb-4">
            <Mail className="h-12 w-12 text-indigo-400" />
          </div>
          <DialogTitle className="text-2xl font-bold text-slate-100">Please Verify Your Email</DialogTitle>
          <DialogDescription className="text-slate-400 mt-2">
            We've sent a verification link to <span className="font-medium text-slate-200">{email}</span>. Please check your inbox and click the link to activate your account.
          </DialogDescription>
        </DialogHeader>
        
        <div className="grid gap-4 py-4">
          {resendMessage && (
            <div className="p-3 bg-green-900/50 border border-green-800 rounded-lg text-green-300 text-sm flex items-center gap-2">
              <CheckCircle className="h-4 w-4" />
              {resendMessage}
            </div>
          )}
          
          {resendError && (
            <div className="p-3 bg-red-900/50 border border-red-800 rounded-lg text-red-300 text-sm">
              {resendError}
            </div>
          )}

          <div className="text-center text-sm text-slate-400 mb-4">
            Didn't receive the email? Check your spam folder or request a new one.
          </div>
          
          <Button 
            onClick={handleResendEmail}
            disabled={isResending}
            variant="outline"
            className="w-full bg-slate-800/50 text-slate-200 hover:bg-slate-700/50 hover:text-slate-100 border-gray-700/50"
          >
            {isResending ? 'Sending...' : 'Resend Verification Email'}
          </Button>
          
          <Button 
            onClick={handleClose}
            className="w-full bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 text-white shadow-[0_8px_32px_rgba(99,102,241,0.3)]"
          >
            I'll Verify Later
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
