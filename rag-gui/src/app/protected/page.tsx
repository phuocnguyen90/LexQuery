import { useSession } from "next-auth/react"
import { redirect } from "next/navigation"

export default function ProtectedPage() {
  const { data: session, status } = useSession({ required: true })

  if (status === 'loading') {
    return <p>Loading...</p>
  }

  if (session?.user?.role !== 'admin') {
    redirect('/') // If not admin, redirect to home
  }

  return (
    <main>
      <h1 className="text-2xl font-bold">Admin Only Content!</h1>
    </main>
  )
}
