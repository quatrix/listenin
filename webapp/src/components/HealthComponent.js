'use strict';

import React from 'react';

var _ = require('lodash')
var moment = require('moment');

require('styles//Health.css');
require('isomorphic-fetch');

var box_states = {
    green: 'Sleeping',
    red: 'Recording',
    blue: 'Uploading',
    purple: 'Waiting for audio',
    orange: 'Problem'
}

var colors = {
}

class AgingTextField extends React.Component {
    render() {
        var style = 'box-text';

        if (!this.props.age || moment().diff(moment(this.props.age), 'minutes') > 5) {
            style = 'box-text-old';
        }

        return <div className={style}>{this.props.text}</div>
    }
}

class BoxHealthComponent extends React.Component {
    render() {
        var health = this.props.health;
        var last_blink = moment(health.last_blink)

        var name = this.props.name.split('-')[1]
        var box_state =  box_states[health.last_color.color]
        var status_led = <div className={'status-led ' + health.last_color.color } />

        return (
            <div className='box'>
                <div className='box-title'>{name}</div>
                {status_led}
                <div className='box-state'>{box_state}</div>

                <AgingTextField
                    age={health.last_color.time}
                    text={'Changed: ' + moment(health.last_color.time).fromNow()}
                />

                <AgingTextField
                    age={health.last_upload.time}
                    text={'Uploaded: ' + moment(health.last_upload.time).fromNow()}
                />

                <AgingTextField
                    age={health.last_blink}
                    text={'Blinked: '+ moment(health.last_blink).fromNow()}
                />
            </div>
        )
    }
}

class HealthComponent extends React.Component {
    constructor(props) {
        super(props);
        this.state = {health: {}}
    }

    getHealth() {
        var self = this

        fetch('http://api.listenin.io/health')
        .then(function(response) {
                if (response.status >= 400) {
                        throw new Error('Bad response from server');
                }
                return response.json();
        })
        .then(function(health) {
                self.setState({health: health});
        });
    }

    componentDidMount() {
        this.getHealth();
        this.timer = setInterval(() => {
            this.getHealth();
        }, 5000);
    }

    render() {
        var i = 0;
        var boxes = _.map(this.state.health, function(v, k) {
            return <BoxHealthComponent
                className='health-component'
                key={i++}
                name={k}
                health={v}
             />
        });

        return (
            <div>
                {boxes}
            </div> 
        );
    }
}

HealthComponent.displayName = 'HealthComponent';

export default HealthComponent;
