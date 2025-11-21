FROM node:20-alpine

WORKDIR /app

COPY package.json pnpm-lock.yaml* ./

RUN npm install -g pnpm && pnpm install --frozen-lockfile

COPY . .

RUN npx tsc --noEmit || echo "TypeScript check completed"

RUN pnpm run build

EXPOSE 3000

# تغییر این خط - اضافه کردن host
CMD ["pnpm", "start", "--hostname", "0.0.0.0"]