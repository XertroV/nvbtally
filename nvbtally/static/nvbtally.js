(function(){
    var refresh_map = {};
    add_refresh = function(tab_name, refresher){
        refresh_map[tab_name] = refresher;
    };
    refresh_name = function(tab_name){
        refresh_map[tab_name]();
    };

    nonNaN = function(number){
        return (!isNaN(number) ? number : 0)
    }

    res_detail_name = '';
    voter_detail_address = '';

    app = angular.module("nvbApp", []);

    app.controller('TabController', ['$log', '$location', function($log, $location){
        var tab = this;
        tab.tabsLeft = ['info', 'resolutions', 'votes'];
        tab.tabsRight = ['voters', 'about'];

        tab.set = function(t){
            tab.current = t;
            $location.hash(t);
            $log.log('Setting tab to: ' + t);
        }
        if ($location.hash() == ''){
            tab.set('info');
        }else{
            tab.set($location.hash());
        }

        tab.is = function(t){
            return (t == tab.current);
        };

        tab.refresh = function(){
            refresh_name(tab.current);
        };

        tab.set_res_detail = function(name){
            res_detail_name = name;
            refresh_name('res_detail');
        };

        tab.set_voter_detail = function(address){
            voter_detail_address = address;
            refresh_name('voter_detail');
        };
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

    app.controller('ResolutionCtrl', ['$log', '$http', '$scope', '$rootScope', function($log, $http, $scope, $rootScope){
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

    app.controller('ResolutionDetailCtrl', ['$log', '$http', '$scope', function($log, $http, $scope){
        var resdet = this;
        resdet.name = '';

        resdet.refresh = function(){
            resdet.res = {};
            resdet.votes = [];
            resdet.name = res_detail_name;
            $log.log(resdet.name);
            if (resdet.name != ''){
                $http.post('/res_detail', {res_name: resdet.name})
                    .success(function(data){
                        resdet.res = data.resolution;
                        resdet.votes = data.votes;
                        $log.log(data.resolution);
                    })
                    .error(function(error,a,b,c){
                    });
            }
        };
        resdet.refresh();
        add_refresh('res_detail', resdet.refresh);
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

    app.controller('VoterDetailCtrl', ['$log', '$http', '$scope', function($log, $http, $scope){
        var votdet = this;

        votdet.refresh = function(){
            votdet.voter = {};
            votdet.votes = [];
            votdet.delegators = [];
            votdet.address = voter_detail_address;
            if (votdet.address != ''){
                $http.post('/voter_detail', {address: votdet.address})
                    .success(function(data){
                        votdet.voter = data.voter;
                        votdet.votes = data.votes;
                        votdet.delegators = data.delegators;
                    })
                    .error(function(error,a,b,c){
                    });
            }
        };
        votdet.refresh();
        add_refresh('voter_detail', votdet.refresh);
    }]);

})();