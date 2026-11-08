/* Panasonic icon set for Home Assistant.
 *
 * Registers the `panasonic:` prefix so the nanoe mark is a first-class icon:
 * it shows up in the icon picker (search "nanoe" or "纳诺怡") and renders
 * wherever an mdi: icon is accepted - entity icons, cards, automations.
 *
 * HA resolves a non-MDI prefix through window.customIcons; without a
 * registered set it falls back to <iron-icon>, which no longer exists in
 * modern frontends and therefore renders blank.
 *
 * Geometry: 44x44 canvas, artwork centred on the same 4.2/6 offset used by
 * brand/nanoe.svg, so the mark keeps the optical size of a 24px MDI glyph.
 * The large disc is polygonised (48 segments, area error below 0.03 percent)
 * because its right edge is a straight vertical chord, which one arc
 * command cannot express.
 */
(() => {
  const ICONS = {
    nanoe: {
      viewBox: "0 0 44 44",
      keywords: ["panasonic", "nanoe", "纳诺怡", "ion", "air", "purifier"],
      path:
        "M26.8,27.37 26.15,28.39 25.4,29.33 24.55,30.18 23.61,30.94 22.59,31.59 21.51,32.12 20.38,32.53 19.21,32.82 18.01,32.97 16.81,32.99 15.61,32.88 14.43,32.64 13.28,32.28 12.18,31.79 11.14,31.18 10.17,30.46 9.28,29.64 8.5,28.73 7.81,27.73 7.24,26.67 6.79,25.55 6.46,24.39 6.27,23.2 6.2,22.0 6.27,20.8 6.46,19.61 6.79,18.45 7.24,17.33 7.81,16.27 8.5,15.27 9.28,14.36 10.17,13.54 11.14,12.82 12.18,12.21 13.28,11.72 14.43,11.36 15.61,11.12 16.81,11.01 18.01,11.03 19.21,11.18 20.38,11.47 21.51,11.88 22.59,12.41 23.61,13.06 24.55,13.82 25.4,14.67 26.15,15.61 26.8,16.63ZM28.6,22.0a4.6,4.6 0 1,0 9.2,0a4.6,4.6 0 1,0 -9.2,0Z",
    },
  };

  window.customIcons = window.customIcons || {};
  window.customIcons.panasonic = {
    getIcon: async (name) => {
      const icon = ICONS[name];
      return icon ? { path: icon.path, viewBox: icon.viewBox } : undefined;
    },
    getIconList: async () =>
      Object.keys(ICONS).map((name) => ({
        name,
        keywords: ICONS[name].keywords,
      })),
  };
})();
