/** Gera core/static/core/app.css a partir dos templates. Rode: npm run build */
module.exports = {
  content: ["../core/templates/**/*.html", "../core/*.py", "../core/templatetags/*.py", "../core/views/*.py"],
  theme: { extend: { fontFamily: { sans: ["Inter", "system-ui", "sans-serif"] } } },
  plugins: [require("daisyui")],
  daisyui: { themes: ["light"], logs: false },
};
