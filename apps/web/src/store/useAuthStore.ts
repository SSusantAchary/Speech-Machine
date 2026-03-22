import { create } from "zustand";
import { authApi, setToken, clearToken } from "@/lib/api";

type AuthState = {
  userEmail: string | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
};

export const useAuthStore = create<AuthState>((set) => ({
  userEmail: null,
  loading: false,
  login: async (email, password) => {
    set({ loading: true });
    try {
      const token = await authApi.login(email, password);
      setToken(token.access_token);
      set({ userEmail: email, loading: false });
    } catch (error) {
      set({ loading: false });
      throw error;
    }
  },
  signup: async (email, password) => {
    set({ loading: true });
    try {
      const token = await authApi.signup(email, password);
      setToken(token.access_token);
      set({ userEmail: email, loading: false });
    } catch (error) {
      set({ loading: false });
      throw error;
    }
  },
  logout: async () => {
    await authApi.logout();
    clearToken();
    set({ userEmail: null });
  },
}));
