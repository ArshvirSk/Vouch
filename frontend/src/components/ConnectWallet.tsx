"use client";

import { usePrivy } from "@privy-io/react-auth";

export function ConnectWallet() {
  const { login, logout, authenticated, user } = usePrivy();

  if (authenticated && user) {
    return (
      <div className="flex items-center gap-2">
        <span className="text-sm text-gray-600">
          {user.wallet?.address ? `${user.wallet.address.slice(0, 6)}...${user.wallet.address.slice(-4)}` : 'Connected'}
        </span>
        <button
          onClick={logout}
          className="text-xs px-2 py-1 bg-gray-200 rounded hover:bg-gray-300"
        >
          Disconnect
        </button>
      </div>
    );
  }

  return (
    <button
      onClick={login}
      className="px-4 py-2 bg-indigo-600 text-white rounded-md text-sm font-medium hover:bg-indigo-700 transition"
    >
      Connect Web3
    </button>
  );
}
