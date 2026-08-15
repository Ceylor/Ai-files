"use client";

/**
 * Анимированная секция — плавное появление содержимого.
 *
 * Props:
 * - children: содержимое.
 * - delay: задержка (ms) перед появлением.
 * - className: доп. классы.
 */
export default function AnimatedSection({ children, delay = 0, className = "" }) {
  return (
    <div
      className={`animate-fade-in-up ${className}`}
      style={{ animationDelay: `${delay}ms` }}
    >
      {children}
    </div>
  );
}