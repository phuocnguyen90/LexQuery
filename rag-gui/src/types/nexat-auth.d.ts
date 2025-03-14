// src/types/next-auth.d.ts

import NextAuth from "next-auth"

declare module "next-auth" {
  interface User {
    id: string
    role: Role
    subscription?: {
      tier: SubscriptionTier
      status: SubscriptionStatus
    }
  }

  interface Session {
    user?: {
      id: string
      name?: string | null
      email?: string | null
      role: Role
      subscription?: {
        tier: SubscriptionTier
        status: SubscriptionStatus
      }
    }
  }
}
