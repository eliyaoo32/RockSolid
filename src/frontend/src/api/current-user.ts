import { createClient } from "@connectrpc/connect"
import { UsersService } from "@rocksolid/api/users/v1/users_pb"
import { useQuery } from "@tanstack/react-query"

import { useApiTransport } from "./transport"

/** The signed-in user, as the backend knows them. */
export function useCurrentUser() {
  const transport = useApiTransport()
  return useQuery({
    queryKey: ["current-user"],
    queryFn: async () => {
      const { user } = await createClient(
        UsersService,
        transport
      ).getCurrentUser({})
      return user
    },
  })
}
