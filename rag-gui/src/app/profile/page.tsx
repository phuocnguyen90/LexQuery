"use client"

import { useSession, signIn, signOut } from "next-auth/react"
import { useState } from "react"

export default function ProfilePage() {
  const { data: session, status } = useSession()
  const [membership, setMembership] = useState("free") // mock membership state
  const [billing, setBilling] = useState("no active subscription") // mock billing status

  if (status === "loading") return <p>Loading...</p>
  if (!session) {
    // Not logged in
    return (
      <main className="max-w-2xl mx-auto p-4">
        <h1 className="text-2xl font-bold mb-4">Please Sign In</h1>
        <button onClick={() => signIn()} className="bg-blue-500 text-white px-4 py-2 rounded">
          Sign In
        </button>
      </main>
    )
  }

  // Example: user is signed in
  // Display profile info, membership and billing
  const handleUpgrade = () => {
    // Mock upgrading membership
    setMembership("paid")
    setBilling("active subscription (expires in 30 days)")
  }

  return (
    <main className="max-w-2xl mx-auto p-4">
      <h1 className="text-2xl font-bold mb-4">Your Profile</h1>
      <p><strong>Username:</strong> {session.user?.name}</p>
      <p><strong>Role:</strong> {session.user?.role || "guest"}</p>
      <p><strong>Membership:</strong> {membership}</p>
      <p><strong>Billing:</strong> {billing}</p>

      <div className="mt-4 space-x-2">
        {membership === "free" && (
          <button onClick={handleUpgrade} className="bg-green-500 text-white px-4 py-2 rounded">
            Upgrade to Paid
          </button>
        )}
        <button onClick={() => signOut()} className="bg-red-500 text-white px-4 py-2 rounded">
          Sign Out
        </button>
      </div>
    </main>
  )
}
