FROM docker.io/kobotoolbox/enketo-express-extra-widgets:7.6.3

LABEL org.opencontainers.image.title="Shopnoltd Enketo"
LABEL org.opencontainers.image.description="Shopnoltd-branded Enketo with scoped numeric beep and auto-advance widget"

COPY shopnoltd-auto-advance-widget.js /srv/src/enketo/node_modules/shopnoltd-auto-advance-widget/shopnoltd-auto-advance-widget.js

RUN node - <<'NODE'
const fs = require('fs');
const path = '/srv/src/enketo/packages/enketo-express/config/default-config.json';
const config = JSON.parse(fs.readFileSync(path, 'utf8'));
const widget = '../../../node_modules/shopnoltd-auto-advance-widget/shopnoltd-auto-advance-widget';
config.widgets = Array.isArray(config.widgets) ? config.widgets : [];
if (!config.widgets.includes(widget)) config.widgets.push(widget);
fs.writeFileSync(path, JSON.stringify(config, null, 4) + '\n');
NODE

RUN yarn workspace enketo-express build
