import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Card } from "@/components/ui/card"
import ProfileTab from "@/components/dashboard/profile-settings/profile-tab"
import AccountTab from "@/components/dashboard/profile-settings/account-tab"
import SecurityTab from "@/components/dashboard/profile-settings/security-tab"
import { User, CreditCard, Shield } from 'lucide-react'

export default function ProfileSettings() {
  return (
    <div className="container-padding py-4 sm:py-6 lg:py-8 max-w-5xl mx-auto">
      <Card className="bg-gray-900/30 border-gray-800/50 backdrop-blur-sm">
        <Tabs defaultValue="profile" className="w-full">
          {/* Tab Navigation */}
          <div className="border-b border-gray-800/50 px-4 sm:px-6 pt-4 sm:pt-6">
            <TabsList className="grid w-full max-w-lg mx-auto grid-cols-3 bg-gray-800/30 border border-gray-700/30 rounded-lg p-1">
              <TabsTrigger
                value="profile"
                className="flex items-center gap-2 data-[state=active]:bg-gray-700/70 data-[state=active]:text-slate-100 data-[state=active]:shadow-sm text-slate-400 rounded-md px-4 py-3 text-sm font-medium transition-all duration-200 hover:text-slate-300"
              >
                <User className="h-4 w-4" />
                <span className="hidden sm:inline">Profile</span>
              </TabsTrigger>
              <TabsTrigger
                value="account"
                className="flex items-center gap-2 data-[state=active]:bg-gray-700/70 data-[state=active]:text-slate-100 data-[state=active]:shadow-sm text-slate-400 rounded-md px-4 py-3 text-sm font-medium transition-all duration-200 hover:text-slate-300"
              >
                <CreditCard className="h-4 w-4" />
                <span className="hidden sm:inline">Account</span>
              </TabsTrigger>
              <TabsTrigger
                value="security"
                className="flex items-center gap-2 data-[state=active]:bg-gray-700/70 data-[state=active]:text-slate-100 data-[state=active]:shadow-sm text-slate-400 rounded-md px-4 py-3 text-sm font-medium transition-all duration-200 hover:text-slate-300"
              >
                <Shield className="h-4 w-4" />
                <span className="hidden sm:inline">Security</span>
              </TabsTrigger>
            </TabsList>
          </div>

          {/* Tab Content */}
          <div className="p-4 sm:p-6">
            <TabsContent value="profile" className="mt-0 space-y-6">
              <ProfileTab />
            </TabsContent>

            <TabsContent value="account" className="mt-0 space-y-6">
              <AccountTab />
            </TabsContent>

            <TabsContent value="security" className="mt-0 space-y-6">
              <SecurityTab />
            </TabsContent>
          </div>
        </Tabs>
      </Card>
    </div>
  )
}
