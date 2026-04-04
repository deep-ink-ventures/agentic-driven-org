import Hero from "@/components/hero";
import ValueProps from "@/components/value-props";
import Product from "@/components/product";
import Consulting from "@/components/consulting";
import Security from "@/components/security";
import Quote from "@/components/quote";
import Waitlist from "@/components/waitlist";
import Footer from "@/components/footer";

export default function Home() {
  return (
    <main>
      <Hero />
      <ValueProps />
      <Product />
      <Consulting />
      <Security />
      <Quote />
      <Waitlist />
      <Footer />
    </main>
  );
}
