
// this file is generated — do not edit it


declare module "svelte/elements" {
	export interface HTMLAttributes<T> {
		'data-sveltekit-keepfocus'?: true | '' | 'off' | undefined | null;
		'data-sveltekit-noscroll'?: true | '' | 'off' | undefined | null;
		'data-sveltekit-preload-code'?:
			| true
			| ''
			| 'eager'
			| 'viewport'
			| 'hover'
			| 'tap'
			| 'off'
			| undefined
			| null;
		'data-sveltekit-preload-data'?: true | '' | 'hover' | 'tap' | 'off' | undefined | null;
		'data-sveltekit-reload'?: true | '' | 'off' | undefined | null;
		'data-sveltekit-replacestate'?: true | '' | 'off' | undefined | null;
	}
}

export {};


declare module "$app/types" {
	export interface AppTypes {
		RouteId(): "/" | "/api" | "/api/users" | "/api/users/[uid]" | "/auth" | "/auth/admin" | "/auth/dashboard" | "/auth/profile" | "/permission" | "/permission/analysis" | "/permission/analysis/[role]" | "/permission/roles" | "/permission/roles/new" | "/permission/roles/[role]" | "/permission/users" | "/permission/users/[userId]";
		RouteParams(): {
			"/api/users/[uid]": { uid: string };
			"/permission/analysis/[role]": { role: string };
			"/permission/roles/[role]": { role: string };
			"/permission/users/[userId]": { userId: string }
		};
		LayoutParams(): {
			"/": { uid?: string; role?: string; userId?: string };
			"/api": { uid?: string };
			"/api/users": { uid?: string };
			"/api/users/[uid]": { uid: string };
			"/auth": Record<string, never>;
			"/auth/admin": Record<string, never>;
			"/auth/dashboard": Record<string, never>;
			"/auth/profile": Record<string, never>;
			"/permission": { role?: string; userId?: string };
			"/permission/analysis": { role?: string };
			"/permission/analysis/[role]": { role: string };
			"/permission/roles": { role?: string };
			"/permission/roles/new": Record<string, never>;
			"/permission/roles/[role]": { role: string };
			"/permission/users": { userId?: string };
			"/permission/users/[userId]": { userId: string }
		};
		Pathname(): "/" | "/api" | "/api/" | "/api/users" | "/api/users/" | `/api/users/${string}` & {} | `/api/users/${string}/` & {} | "/auth" | "/auth/" | "/auth/admin" | "/auth/admin/" | "/auth/dashboard" | "/auth/dashboard/" | "/auth/profile" | "/auth/profile/" | "/permission" | "/permission/" | "/permission/analysis" | "/permission/analysis/" | `/permission/analysis/${string}` & {} | `/permission/analysis/${string}/` & {} | "/permission/roles" | "/permission/roles/" | "/permission/roles/new" | "/permission/roles/new/" | `/permission/roles/${string}` & {} | `/permission/roles/${string}/` & {} | "/permission/users" | "/permission/users/" | `/permission/users/${string}` & {} | `/permission/users/${string}/` & {};
		ResolvedPathname(): `${"" | `/${string}`}${ReturnType<AppTypes['Pathname']>}`;
		Asset(): "/data.json" | "/robots.txt" | string & {};
	}
}