import Image from "next/image";

export default function Home() {
  return (
    <div className="relative min-h-screen w-full overflow-hidden font-sans">
      <Image
        src="/bg.png"
        alt="J'Bistro cozy restaurant background"
        fill
        className="object-cover brightness-[0.85]"
        priority
        quality={90}
      />

      {/* Overlay for better text readability */}
      <div className="absolute inset-0 bg-gradient-to-b from-black/30 via-black/20 to-black/40 z-10" />

      {/* Main Content */}
      <div className="relative z-20 flex min-h-screen flex-col items-center justify-center px-6 py-12 text-center">
        {/* Logo / Header */}
        <div className="mb-10 flex flex-col items-center gap-3">
          <Image
            src="/plogo.png"
            alt="J'Bistro Logo"
            width={280}
            height={120}
            className="drop-shadow-xl"
            priority
          />

          <h1 className="text-5xl md:text-6xl font-extrabold tracking-tight text-white drop-shadow-2xl">
            J&apos;Bistro
          </h1>

          <p className="text-xl font-semibold uppercase tracking-wider text-white drop-shadow-lg">
            RESTAURANT
          </p>
        </div>

        {/* Welcome Text */}
        <h2 className="mb-10 text-4xl md:text-5xl font-bold text-white drop-shadow-2xl leading-tight">
          Welcome to<br />
          J&apos;Bistro
        </h2>

        <div className="w-full max-w-md rounded-3xl bg-[#f5e0c2]/85 p-10 shadow-2xl backdrop-blur-sm border border-amber-800/30">
          <form className="flex flex-col gap-6">
            {/* Email */}
            <div className="flex flex-col text-left">
              <label htmlFor="email" className="mb-2 text-lg font-medium text-gray-800">
                Email
              </label>
              <input
                type="email"
                id="email"
                placeholder=""
                required
                className="rounded-xl border border-amber-700/50 bg-white/70 px-5 py-4 text-gray-800 placeholder-gray-500 focus:border-amber-600 focus:ring-2 focus:ring-amber-500 focus:outline-none"
              />
            </div>

            {/* Password */}
            <div className="flex flex-col text-left">
              <label htmlFor="password" className="mb-2 text-lg font-medium text-gray-800">
                Password
              </label>
              <input
                type="password"
                id="password"
                placeholder=""
                required
                className="rounded-xl border border-amber-700/50 bg-white/70 px-5 py-4 text-gray-800 placeholder-gray-500 focus:border-amber-600 focus:ring-2 focus:ring-amber-500 focus:outline-none"
              />
            </div>

            {/* Login Button */}
            <button
              type="submit"
              className="mt-4 rounded-xl bg-amber-800 px-10 py-4 text-xl font-bold text-white shadow-lg transition hover:bg-amber-900 active:scale-95"
            >
              Login
            </button>
          </form>
        </div>

        {/* Register Link */}
        <p className="mt-8 text-lg text-white/90">
          Don&apos;t have an account?{" "}
          <a
            href="/register"
            className="font-semibold text-amber-300 underline hover:text-amber-200 transition"
          >
            Register here
          </a>
        </p>
      </div>
    </div>
  );
}