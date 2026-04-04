export default function Footer() {
  return (
    <footer className="py-16 px-6 md:px-12">
      <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-start sm:items-center justify-between gap-6 text-sm text-silver">
        <span className="font-display font-medium text-white tracking-[-0.01em]">
          AgentDriven
        </span>
        <div className="flex flex-col sm:flex-row gap-4 sm:gap-8">
          <a
            href="mailto:hello@agentdriven.org"
            className="hover:text-white transition-colors duration-200"
          >
            hello@agentdriven.org
          </a>
          <span className="text-silver/50">
            &copy; {new Date().getFullYear()}
          </span>
        </div>
      </div>
    </footer>
  );
}
