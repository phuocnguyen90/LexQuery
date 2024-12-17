import './globals.css'
import type { Metadata } from 'next'
import { ReactNode } from 'react'
import NavBar from "@/components/NavBar"
import Provider from "@/components/Provider"

export const metadata: Metadata = {
  title: 'My RAG App',
  description: 'A sophisticated RAG pipeline interface with authentication and roles',
}

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Provider>
          <NavBar />
          {children}
        </Provider>
      </body>
    </html>
  )
}
