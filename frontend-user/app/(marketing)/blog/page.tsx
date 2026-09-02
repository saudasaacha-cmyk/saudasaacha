import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import {
  MpCard,
  MpPageHero,
  MpSection,
} from "@/components/marketing/mp-ui";
import { BLOG_CATEGORIES, BLOG_POSTS } from "./posts";

export const metadata: Metadata = {
  title: "The SaudaSaacha Blog — Investing, Markets & Risk Management",
  description:
    "Practical writing on getting started, trading Indian markets, managing risk and using the platform. No hype, no recycled tips.",
};

export default function BlogIndexPage() {
  return (
    <>
      <MpPageHero
        eyebrow="Blog"
        title="Clear, practical writing on investing in Indian markets."
        lead="We write about getting started, trading Equity and F&O, managing risk, and using the platform well. No “5 secret indicators,” no recycled listicles."
      />

      <MpSection>
        {/* Categories */}
        <div className="flex flex-wrap gap-2">
          {BLOG_CATEGORIES.map((c) => (
            <span
              key={c}
              className="rounded-full border border-mp-border bg-mp-surface px-3.5 py-1.5 text-xs font-medium text-mp-text-mut"
            >
              {c}
            </span>
          ))}
        </div>

        {/* Posts */}
        <div className="mt-10 grid gap-5 lg:grid-cols-3">
          {BLOG_POSTS.map((post) => (
            <MpCard key={post.slug} className="flex flex-col gap-3">
              <span className="text-xs font-semibold uppercase tracking-wide text-mp-primary">
                {post.category}
              </span>
              <h2 className="font-display text-lg font-semibold leading-snug text-mp-text">
                <Link href={`/blog/${post.slug}`} className="hover:text-mp-primary">
                  {post.title}
                </Link>
              </h2>
              <p className="text-sm leading-[1.6] text-mp-text-mut">{post.excerpt}</p>
              <Link
                href={`/blog/${post.slug}`}
                className="mt-auto inline-flex items-center gap-1 text-sm font-semibold text-mp-primary hover:text-mp-primary-2"
              >
                Read post
                <ArrowRight className="size-4" />
              </Link>
            </MpCard>
          ))}
        </div>
      </MpSection>
    </>
  );
}
