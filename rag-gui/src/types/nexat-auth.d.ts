import NextAuth from "next-auth"

declare module "next-auth" {
  interface User {
    id: string
    role?: string
  }

  interface Session {
    user?: {
      id: string
      name?: string
      role?: string
    }
  }

  // Optionally, extend JWT if needed
  // interface JWT {
  //   id?: string
  //   role?: string
  // }
}
