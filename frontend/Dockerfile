FROM node:20-slim

WORKDIR /app

COPY package*.json ./
# Use --legacy-peer-deps to handle Svelte 5 peer dependency conflicts
RUN npm install --legacy-peer-deps

COPY . .

# Ensure .svelte-kit is generated
RUN npx svelte-kit sync

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
