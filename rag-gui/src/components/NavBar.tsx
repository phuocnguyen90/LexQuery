'use client'

import Link from "next/link"
import { useSession, signIn, signOut } from "next-auth/react"

export default function NavBar() {
  const { data: session, status } = useSession()

  return (
    <nav className="bg-gray-800 p-4">
      <div className="max-w-7xl mx-auto flex justify-between items-center">
        <div>
          <Link href="/" className="text-white font-bold text-xl">RAG App</Link>
        </div>
        <div className="space-x-4">
          <Link href="/chat" className="text-gray-300 hover:text-white">Chat</Link>
          <Link href="/profile" className="text-gray-300 hover:text-white">Profile</Link>
          {!session && (
            <>
              <Link href="/register" className="text-gray-300 hover:text-white">Register</Link>
              <button onClick={() => signIn()} className="text-gray-300 hover:text-white">Sign In</button>
            </>
          )}
          {session && (
            <button onClick={() => signOut()} className="text-gray-300 hover:text-white">Sign Out</button>
          )}
        </div>
      </div>
    </nav>
  )
}
