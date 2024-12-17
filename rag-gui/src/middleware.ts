// src/middleware.ts

import { withAuth } from "next-auth/middleware"
import { NextResponse } from "next/server"

export default withAuth(
  function middleware(req) {
    const { pathname } = req.nextUrl

    // Protect admin and moderator routes
    if (pathname.startsWith("/admin") || pathname.startsWith("/moderator")) {
      const session = req.nextauth.token

      if (!session || (session.role !== "ADMIN" && session.role !== "MODERATOR")) {
        return NextResponse.redirect(new URL("/signin", req.url))
      }
    }

    return NextResponse.next()
  },
  {
    callbacks: {
      authorized({ token }) {
        // Allow all requests if token exists
        return !!token
      },
    },
  }
)

// Define which paths should use this middleware
export const config = {
  matcher: ["/admin/:path*", "/moderator/:path*"],
}
