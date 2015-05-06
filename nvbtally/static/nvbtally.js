(function(){
    var refresh_map = {};
    add_refresh = function(tab_name, refresher){
        refresh_map[tab_name] = refresher;
    };
    refresh_name = function(tab_name){
        refresh_map[tab_name]();
    };

    app = angular.module("nvbApp", []);

    app.controller('TabController', ['$log', function($log){
        var tab = this;
        tab.tabsLeft = ['info', 'resolutions', 'votes'];
        tab.tabsRight = ['voters', 'about'];

        tab.set = function(t){
            tab.current = t;
            $log.log('Setting tab to: ' + t);
        }
        tab.set('info');

        tab.is = function(t){
            return (t == tab.current);
        }

        tab.refresh = function(){
            refresh_name(tab.current);
        }
    }]);

    app.controller('InfoCtrl', ['$log', '$http', function($log, $http){
        var info = this;

        info.refresh = function(){
            info.content = {};
            $http.get('/info')
                .success(function(data){
                    info.content = data;
                    $log.log(data);
                }).error(function(error,and,other,things){
                    $log.log(error);
                });
        };
        info.refresh();
        add_refresh('info', info.refresh);
    }]);

    app.controller('ResolutionCtrl', ['$log', '$http', function($log, $http){
        var res = this;

        res.refresh = function(){
            res.unfinalized = [];
            res.finalized = [];
            $http.get('/resolutions')
            .success(function(data){
                res.unfinalized = data.unfinalized;
                res.finalized = data.finalized;
            }).error(function(error,and,other,things){
            });
        };
        res.refresh();
        add_refresh('resolutions', res.refresh);
    }]);

    app.controller('VotesCtrl', ['$log', '$http', function($log, $http){
        $log.log(this);
        var votes = this;

        votes.refresh = function(){
            votes.list = [];
            $http.get('/votes')
                .success(function(data){
                    votes.list = data.votes;
                    $log.log(data.votes);
                })
                .error(function(error,a,b,c){
                });
        };
        votes.refresh();
        add_refresh('votes', votes.refresh);
    }]);

    app.controller('VotersCtrl', ['$log', '$http', function($log, $http){
        var voters = this;

        voters.refresh = function(){
            voters.list = [];
            $http.get('/voters')
                .success(function(data){
                    voters.list = data.voters;
                    $log.log(data.voters);
                })
                .error(function(error,a,b,c){
                });
        };
        voters.refresh();
        add_refresh('voters', voters.refresh);
    }]);

})();