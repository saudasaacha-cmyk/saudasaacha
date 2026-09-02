import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft, ArrowRight } from "lucide-react";
import {
  MpButton,
  MpContainer,
  MpSection,
} from "@/components/marketing/mp-ui";
import { BLOG_POSTS, getPost } from "../posts";

export function generateStaticParams() {
  return BLOG_POSTS.map((p) => ({ slug: p.slug }));
}

export function generateMetadata({
  params,
}: {
  params: { slug: string };
}): Metadata {
  const post = getPost(params.slug);
  if (!post) return { title: "Post not found | SaudaSaacha" };
  return { title: post.seoTitle, description: post.seoDescription };
}

export default function BlogPostPage({
  params,
}: {
  params: { slug: string };
}) {
  const post = getPost(params.slug);
  if (!post) notFound();

  return (
    <>
      <section className="mp-dark relative overflow-hidden bg-mp-bg text-mp-text">
        <div className="mp-grid-lines absolute inset-0 opacity-25" aria-hidden />
        <MpContainer className="relative pb-16 pt-28 sm:pb-20 sm:pt-32">
          <div className="max-w-3xl">
            <Link
              href="/blog"
              className="inline-flex items-center gap-1 text-sm font-medium text-mp-text-mut hover:text-mp-text"
            >
              <ArrowLeft className="size-4" />
              All posts
            </Link>
            <span className="mt-6 block text-xs font-semibold uppercase tracking-wide text-mp-primary">
              {post.category}
            </span>
            <h1 className="mt-3 font-display text-3xl font-bold leading-[1.1] text-mp-text sm:text-4xl">
              {post.title}
            </h1>
          </div>
        </MpContainer>
      </section>

      <MpSection>
        <article className="flex max-w-mp-prose flex-col gap-6">
          {post.body.map((para, i) => (
            <p key={i} className="text-base leading-[1.7] text-mp-text">
              {para}
            </p>
          ))}
          <p className="mt-2 border-l-2 border-mp-gold/60 pl-4 text-sm italic leading-[1.6] text-mp-text-mut">
            {post.riskWarning}
          </p>
        </article>

        <div className="mt-12 border-t border-mp-border pt-8">
          <MpButton href="/register">
            Open Account
            <ArrowRight className="size-4" />
          </MpButton>
        </div>
      </MpSection>
    </>
  );
}
