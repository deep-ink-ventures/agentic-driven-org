export default function Footer() {
  return (
    <footer className="py-12 px-6 border-t border-silver/10">
      <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4 text-sm text-silver">
        <span className="font-medium text-white">AgentDriven</span>
        <span>&copy; {new Date().getFullYear()} AgentDriven. All rights reserved.</span>
        <a
          href="mailto:hello@agentdriven.org"
          className="hover:text-white transition-colors"
        >
          hello@agentdriven.org
        </a>
      </div>
    </footer>
  );
}
