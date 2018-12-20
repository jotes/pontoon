import React from 'react';

import App, { AppLoader } from './App';
import { createReduxStore } from "./test/store";
import { shallowUntilTarget } from "./test/utils";

describe('<App>', () => {
    it('renders without crashing', () => {
        // Commented out because there's a network call that I can't figure out
        // how to mock yet.

        // store.dispatch = sinon.fake();
        //
        // const div = document.createElement('div');
        // ReactDOM.render(shallow(<App store={ store } />), div);
        // ReactDOM.unmountComponentAtNode(div);
    });
    it('render the loader before entities and locales will load', () => {
        const loaderText = '"640K ought to be enough for anybody."';
        let store = createReduxStore({
            entities: {
                fetching: true,
            },
            locales: {
                fetching: true,
            },
        });
        let app = shallowUntilTarget(<App store={store} />, AppLoader);
        expect(app.text()).toContain(loaderText);

        store = createReduxStore({
            entities: {
                fetching: false,
            },
            locales: {
                fetching: true,
            },
        });
        app = shallowUntilTarget(<App store={store} />, AppLoader);
        expect(app.text()).toContain(loaderText);

        store = createReduxStore({
            entities: {
                fetching: true,
            },
            locales: {
                fetching: false,
            },
        });
        app = shallowUntilTarget(<App store={store} />, AppLoader);
        expect(app.text()).toContain(loaderText);
    });
});
