require('normalize.css/normalize.css');
require('styles/App.css');

import React from 'react';
import HealthComponent from './HealthComponent.js'

class AppComponent extends React.Component {
  render() {
    return (
        <HealthComponent />
    );
  }
}

AppComponent.defaultProps = {
};

export default AppComponent;
