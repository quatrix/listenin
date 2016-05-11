'use strict';

import React from 'react';
import { Table } from 'react-bootstrap';


var _ = require('lodash')
var moment = require('moment');

require('styles//Health.css');
require('isomorphic-fetch');


var box_states = {
    green: 'Sleeping',
    red: 'Recording',
    blue: 'Uploading',
    purple: 'Waiting for signal',
    orange: 'Problem'
}

var colors = {
    green: '#2ecc71',
    red: '#e74c3c',
    orange: '#f39c12',
    blue: '#3498db',
    purple: '#9b59b6'
}

class BoxHealthComponent extends React.Component {
    render() {

        var health = this.props.health;
        var now = moment();
        var last_blink = moment(health.last_blink)

        var last_color_style = {'backgroundColor': colors[health.last_color.color]}
        var row_style = {}

        var name = this.props.name.split('-')[1]
        var box_state =  box_states[health.last_color.color]

        if (last_blink.diff(now, 'minutes') > 1) {
            row_style = {'textDecoration': 'line-through'}
        }

        return (
            <tr style={row_style}>
                <td style={last_color_style}></td>
                <td>{name}</td>
                <td>{box_state}</td>
                <td>{moment(health.last_color.changed_at).fromNow()}</td>
                <td>{moment(health.last_blink).fromNow(true)}</td>
            </tr>
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
            return <BoxHealthComponent key={i++} name={k} health={v} />
        });

        return (
            <Table condensed>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>name</th>
                        <th>state</th>
                        <th>state change</th>
                        <th>blink</th>
                    </tr>
                </thead>
                <tbody>
                {boxes}
                </tbody>
            </Table>
        );
    }
}

HealthComponent.displayName = 'HealthComponent';

export default HealthComponent;
