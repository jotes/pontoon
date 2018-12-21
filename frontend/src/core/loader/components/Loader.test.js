import React from 'react';
import Loader from './Loader';

import { createReduxStore } from "../../../test/store";
import { shallowUntilTarget } from "../../../test/utils";

const MockApp = (
    <div>
        Pontoon
    </div>
);

function getLoader(store, waitComponent) {
  return shallowUntilTarget(
      <Loader store={store}>
          <MockApp />
      </Loader>, waitComponent ? waitComponent : Loader
  )
}

describe('<Loader>', () => {
    const loaderText = '"640K ought to be enough for anybody."';

    it('render the loader before l10n bundle will be fetched', () => {
        const store = createReduxStore({
           l10n:{
               fetching: true,
           },
        });

        const loader = getLoader(store);
        expect(loader.text()).toContain(loaderText);
    });

    it('render the loader before locales will be fetched', () => {
    });

    it('render the loader before entities will be fetched', () => {

    });
    it('render the app when pontoon requests the next batch of entities', () => {

    });
    it('render the app if all resources are fetched', () => {

    });
    // it('render the loader before entities and locales will load', () => {
    //     let store = createReduxStore({
    //         entities: {
    //             fetching: true,
    //         },
    //         locales: {
    //             fetching: true,
    //         },
    //     });
    //     let app = sghallowUntilTarget(<App store={store} />, AppLoader);
    //     expect(app.text()).toContain(loaderText);
    //
    //     store = createReduxStore({
    //         entities: {
    //             fetching: false,
    //         },
    //         locales: {
    //             fetching: true,
    //         },
    //     });
    //     app = shallowUntilTarget(<App store={store} />, AppLoader);
    //     expect(app.text()).toContain(loaderText);
    //
    //     store = createReduxStore({
    //         entities: {
    //             fetching: true,
    //         },
    //         locales: {
    //             fetching: false,
    //         },
    //     });
    //     app = shallowUntilTarget(<App store={store} />, AppLoader);
    //     expect(app.text()).toContain(loaderText);
    // });
});
