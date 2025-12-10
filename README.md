# sv

Everything you need to build a Svelte project, powered by [`sv`](https://github.com/sveltejs/cli).

## Creating a project

If you're seeing this, you've probably already done this step. Congrats!

```sh
# create a new project in the current directory
npx sv create

# create a new project in my-app
npx sv create my-app
```

## Developing

Once you've created a project and installed dependencies with `npm install` (or `pnpm install` or `yarn`), start a development server:

```sh
npm run dev

# or start the server and open the app in a new browser tab
npm run dev -- --open
```

## Building

To create a production version of your app:

```sh
npm run build
```

You can preview the production build with `npm run preview`.

> To deploy your app, you may need to install an [adapter](https://svelte.dev/docs/kit/adapters) for your target environment.



give me a full svelte app with firebase auth
 - firebase auth emulator option to choose
 - firebase emulator runs in a seperate docker container
 - user creation, update and roles are stored in backend by calling api
 - User will first land in landing page (no auth)
 - landing page will have login button
 -  after auth users land in a first auth page from there user can go to diff auth pages... all pages are protected meaning wihtout auth navigation is not allowed
- first auth page should run in server side and get the required date before loading at client
- use tailwind
- don't show the navigation path in the url --- possible  in svelte?
- don't give me backend code... instead give me the api with mock and store the date in a text file in json


docker clean uP
1- Stop all containers
docker stop $(docker ps -aq)

2- Remove all containers
docker rm $(docker ps -aq)

3- Prune system
docker system prune -a --volumes

4- Remove all images
docker rmi $(docker images -aq)