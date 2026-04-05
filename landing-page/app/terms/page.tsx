import Link from "next/link";

export const metadata = {
  title: "Terms of Service — The Agent Driven Organization",
};

export default function Terms() {
  return (
    <div className="min-h-screen px-6 md:px-12 py-24 md:py-40">
      <div className="max-w-2xl mx-auto">
        <Link
          href="/"
          className="text-stone text-sm hover:text-white transition-colors duration-200 mb-12 inline-block"
        >
          &larr; Back to home
        </Link>

        <h1 className="font-display text-3xl md:text-5xl font-normal tracking-[-0.02em] leading-[1.1] mb-10">
          Terms of Service
        </h1>

        <div className="space-y-6 text-[16px] text-stone leading-relaxed">
          <p>
            These terms of service are a placeholder. They will be updated with
            the full The Agent Driven Organization terms before launch.
          </p>
          <p>
            If you have questions, contact us at{" "}
            <a
              href="mailto:hello@agentdriven.org"
              className="text-copper hover:text-copper-light transition-colors duration-200"
            >
              hello@agentdriven.org
            </a>.
          </p>
        </div>
      </div>
    </div>
  );
}
