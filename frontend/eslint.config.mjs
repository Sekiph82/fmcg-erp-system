import nextVitals from "eslint-config-next/core-web-vitals";

const eslintConfig = [
  ...nextVitals,
  {
    ignores: [".next/**", "node_modules/**", "out/**", "build/**", "next-env.d.ts"],
    rules: {
      // The upgraded plugin enabled React Compiler diagnostics across this
      // legacy app; keep the established hook and navigation lint baseline.
      "react-hooks/set-state-in-effect": "off",
      "react-hooks/immutability": "off",
      "react-hooks/purity": "off",
      "react-hooks/static-components": "off",
      "@next/next/no-html-link-for-pages": "off",
    },
  },
];

export default eslintConfig;
