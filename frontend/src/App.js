/* @flow */

import React from 'react';
import { connect } from 'react-redux';

import './App.css';

import { Lightbox } from 'core/lightbox';
import * as locales from 'core/locales';
import { selectors as navSelectors } from 'core/navigation';
import { UserAutoUpdater } from 'core/user';
import { EntitiesList } from 'modules/entitieslist';
import { EntityDetails } from 'modules/entitydetails';

import type {State as EntitiesState} from 'modules/entitieslist/reducer';
import type { LocaleState } from 'modules/core/locales/reducer'
import type { Navigation } from 'core/navigation';


type Props = {|
    entities: EntitiesState,
    locales: LocaleState,
    parameters: Navigation,
|};

type InternalProps = {|
    ...Props,
    dispatch: Function,
|};

export const AppLoader = () => (
    <div id="project-load" className="overlay">
        <div className="inner">
            <div className="animation">
                  <div></div>&nbsp;
                  <div></div>&nbsp;
                  <div></div>&nbsp;
                  <div></div>&nbsp;
                  <div></div>
            </div>
            <div className="text">&quot;640K ought to be enough for anybody.&quot;</div>
        </div>
    </div>
);

/**
 * Main entry point to the application. Will render the structure of the page.
 */
class App extends React.Component<InternalProps> {
    componentDidMount() {
        this.props.dispatch(locales.actions.get());
    }

    render() {
        const {entities, locales} = this.props;

        if (entities.fetching || locales.fetching) {
            return <AppLoader />
        }

        return <div id="app">
            <UserAutoUpdater />
            <section>
                <EntitiesList />
            </section>
            <EntityDetails />
            <Lightbox />
        </div>;
    }
}

const mapStateToProps = (state: Object): Props => {
    const {entities, locales} = state;

    return {
        entities,
        locales,
        parameters: navSelectors.getNavigation(state),
    };
};

export default connect(mapStateToProps)(App);
