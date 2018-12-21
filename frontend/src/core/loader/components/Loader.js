/* @flow */

import React from 'react';
import { connect } from 'react-redux';

import './Loader.css';

import { Lightbox } from 'core/lightbox';
import * as locales from 'core/locales';
import { selectors as navSelectors } from 'core/navigation';
import { UserAutoUpdater } from 'core/user';
import { EntitiesList } from 'modules/entitieslist';
import { EntityDetails } from 'modules/entitydetails';

import type { State as EntitiesState } from 'modules/entitieslist/reducer';
import type { LocaleState } from 'modules/core/locales/reducer';
import type { L10nState } from 'modules/core/l10n/reducer';
import type { Navigation } from 'core/navigation';

type Props = {|
    l10n: L10nState,
    entities: EntitiesState,
    locales: LocaleState,
|};

type InternalProps = {|
    ...Props,
    dispatch: Function,
|};

const LoadingBar = () => (
    <div id="project-load" className="overlay">
        <div className="inner">
            <div className="animation">
                <div></div>
                &nbsp;
                <div></div>
                &nbsp;
                <div></div>
                &nbsp;
                <div></div>
                &nbsp;
                <div></div>
            </div>
            <div className="text">&quot;640K ought to be enough for anybody.&quot;</div>
        </div>
    </div>
);

export class Loader extends React.Component<InternalProps> {
    render() {
        const { l10n, entities, locales, children } = this.props;
        const isLoading = (
            l10n.fetching ||
            locales.fetching ||
            (entities.fetching && entities.entities.length == 0)
        );

        return (
            <React.Fragment>
                { isLoading ? <LoadingBar /> : '' }
                { children }
            </React.Fragment>
        );
    }
}

const mapStateToProps = (state: Object): Props => {
    const { l10n, locales, entities } = state;

    return {
        l10n,
        locales,
        entities,
    };
};

export default connect(mapStateToProps)(Loader);
