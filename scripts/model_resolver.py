#!/usr/bin/env python3
"""
ComfyUI Model Resolver CLI

Main command-line interface for the model dependency resolver.
"""

import click
import json
import sys
from pathlib import Path
from typing import Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.workflow_analyzer import WorkflowAnalyzer
from src.core.model_matcher import ModelMatcher
from src.core.keyword_extractor import KeywordExtractor
from src.integrations.hf_searcher import HuggingFaceSearcher
from src.integrations.downloader import ModelDownloader
from src.utils.config_loader import ConfigLoader
from src.utils.cache_manager import CacheManager
from src.utils.logger import setup_colored_logger


# Setup logger
logger = setup_colored_logger()


@click.group()
@click.option('--config', '-c', type=click.Path(exists=True), 
              help='Path to configuration file')
@click.option('--base-path', '-b', type=click.Path(exists=True),
              help='Base path for ComfyUI models')
@click.pass_context
def cli(ctx, config, base_path):
    """ComfyUI Model Dependency Resolver"""
    # Load configuration
    config_loader = ConfigLoader(config) if config else ConfigLoader()
    
    # Override base path if provided
    if base_path:
        config_loader.config['paths']['models_base'] = base_path
    
    # Store in context
    ctx.ensure_object(dict)
    ctx.obj['config'] = config_loader
    ctx.obj['base_path'] = base_path or config_loader.get('paths.models_base', '/workspace/comfyui/models')


@cli.command()
@click.argument('workflow_file', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), 
              help='Output file for analysis results')
@click.pass_context
def analyze(ctx, workflow_file, output):
    """Analyze a workflow file and extract model dependencies."""
    analyzer = WorkflowAnalyzer()
    
    try:
        logger.info(f"Analyzing workflow: {workflow_file}")
        result = analyzer.analyze_workflow(workflow_file)
        
        # Display results
        click.echo(f"\nWorkflow Analysis Results:")
        click.echo(f"Total nodes: {result['total_nodes']}")
        click.echo(f"Model dependencies: {result['model_count']}")
        
        if result['models']:
            click.echo("\nExtracted models:")
            for model in result['models']:
                click.echo(f"  - {model['filename']} ({model['model_type']})")
        
        # Save to file if requested
        if output:
            with open(output, 'w') as f:
                json.dump(result, f, indent=2)
            logger.info(f"Results saved to: {output}")
            
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        sys.exit(1)


@cli.command()
@click.argument('workflow_file', type=click.Path(exists=True))
@click.option('--no-cache', is_flag=True, help='Disable cache usage')
@click.option('--threshold', '-t', type=float, default=0.7,
              help='Similarity threshold for partial matches')
@click.option('--export', '-e', type=click.Path(),
              help='Export missing models to JSON file')
@click.pass_context
def check(ctx, workflow_file, no_cache, threshold, export):
    """Check workflow models against local installation."""
    base_path = ctx.obj['base_path']
    matcher = ModelMatcher(base_path, similarity_threshold=threshold)
    
    try:
        logger.info(f"Checking models for: {workflow_file}")
        results = matcher.match_workflow_models(workflow_file, use_cache=not no_cache)
        
        # Display report
        report = matcher.generate_report(results)
        click.echo(report)
        
        # Export missing models if requested
        if export:
            missing_data = matcher.export_missing_models(results)
            with open(export, 'w') as f:
                json.dump(missing_data, f, indent=2)
            logger.info(f"Missing models exported to: {export}")
            
    except Exception as e:
        logger.error(f"Check failed: {e}")
        sys.exit(1)


@cli.command()
@click.argument('models_file', type=click.Path(exists=True))
@click.option('--use-cache/--no-cache', default=True,
              help='Use cached search results')
@click.option('--output', '-o', type=click.Path(),
              help='Output file for search results')
@click.pass_context
def search(ctx, models_file, use_cache, output):
    """Search for models on HuggingFace."""
    # Load models to search
    with open(models_file, 'r') as f:
        data = json.load(f)
    
    models = data.get('missing', []) + data.get('models', [])
    if not models:
        logger.warning("No models to search")
        return
    
    # Setup searcher
    cache_manager = CacheManager() if use_cache else None
    searcher = HuggingFaceSearcher(cache_manager)
    
    logger.info(f"Searching for {len(models)} models...")
    
    # Search for each model
    results = {
        'found': [],
        'not_found': []
    }
    
    for model in models:
        filename = model.get('name') or model.get('filename')
        if not filename:
            continue
            
        logger.info(f"Searching: {filename}")
        result = searcher.search_sync(filename, use_cache)
        
        if result:
            model['url'] = result['url']
            model['repo_id'] = result['repo_id']
            results['found'].append(model)
            click.echo(f"  ✓ Found: {filename} -> {result['repo_id']}")
        else:
            results['not_found'].append(model)
            click.echo(f"  ✗ Not found: {filename}")
    
    # Summary
    click.echo(f"\nSearch Results:")
    click.echo(f"  Found: {len(results['found'])}")
    click.echo(f"  Not found: {len(results['not_found'])}")
    
    # Save results
    if output:
        with open(output, 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"Results saved to: {output}")


@cli.command()
@click.argument('download_file', type=click.Path(exists=True))
@click.option('--dry-run', is_flag=True, help='Show what would be downloaded')
@click.option('--concurrent', '-j', type=int, default=3,
              help='Number of concurrent downloads')
@click.pass_context
def download(ctx, download_file, dry_run, concurrent):
    """Download models from a JSON file."""
    base_path = ctx.obj['base_path']
    config = ctx.obj['config']
    
    # Load download list
    with open(download_file, 'r') as f:
        data = json.load(f)
    
    # Extract models with URLs
    download_list = []
    for model in data.get('found', []) + data.get('models', []):
        if 'url' in model:
            download_list.append({
                'name': model.get('name') or model.get('filename'),
                'type': model.get('type') or model.get('model_type'),
                'url': model['url']
            })
    
    if not download_list:
        logger.warning("No models to download")
        return
    
    if dry_run:
        click.echo(f"Would download {len(download_list)} models:")
        for item in download_list:
            click.echo(f"  - {item['name']} ({item['type']})")
        return
    
    # Setup downloader
    downloader = ModelDownloader(base_path, config)
    downloader.max_concurrent = concurrent
    
    # Progress callback
    def progress_callback(**kwargs):
        filename = kwargs.get('filename', '')
        progress = kwargs.get('progress', 0)
        speed = kwargs.get('speed', 0)
        click.echo(f"\r{filename}: {progress:.1f}% ({speed:.1f} MB/s)", nl=False)
    
    logger.info(f"Downloading {len(download_list)} models...")
    
    # Download
    results = downloader.batch_download_sync(download_list)
    
    # Summary
    click.echo(f"\n\nDownload Summary:")
    click.echo(f"  Success: {results['success']}/{results['total']}")
    
    if results['failed']:
        click.echo(f"  Failed downloads:")
        for name in results['failed']:
            click.echo(f"    - {name}")


@cli.command()
@click.argument('workflow_file', type=click.Path(exists=True))
@click.option('--download/--no-download', default=True,
              help='Automatically download missing models')
@click.option('--threshold', '-t', type=float, default=0.7,
              help='Similarity threshold for partial matches')
@click.pass_context
def resolve(ctx, workflow_file, download, threshold):
    """Complete workflow resolution: analyze, check, search, and download."""
    base_path = ctx.obj['base_path']
    config = ctx.obj['config']
    
    # Step 1: Analyze workflow
    logger.info("Step 1: Analyzing workflow...")
    analyzer = WorkflowAnalyzer()
    analysis = analyzer.analyze_workflow(workflow_file)
    
    # Step 2: Check local models
    logger.info("Step 2: Checking local models...")
    matcher = ModelMatcher(base_path, similarity_threshold=threshold)
    match_results = matcher.match_workflow_models(workflow_file)
    
    # Display initial report
    report = matcher.generate_report(match_results)
    click.echo(report)
    
    if not match_results['missing']:
        logger.info("All models found locally!")
        return
    
    # Step 3: Search for missing models
    logger.info("Step 3: Searching for missing models...")
    missing_data = matcher.export_missing_models(match_results)
    
    cache_manager = CacheManager()
    searcher = HuggingFaceSearcher(cache_manager)
    
    download_list = []
    for model in missing_data['missing']:
        filename = model['name']
        logger.info(f"Searching: {filename}")
        
        result = searcher.search_sync(filename)
        if result:
            download_list.append({
                'name': filename,
                'type': model['type'],
                'url': result['url']
            })
            click.echo(f"  ✓ Found: {filename}")
        else:
            click.echo(f"  ✗ Not found: {filename}")
    
    if not download_list:
        logger.warning("No downloadable models found")
        return
    
    # Step 4: Download if requested
    if download:
        logger.info(f"Step 4: Downloading {len(download_list)} models...")
        downloader = ModelDownloader(base_path, config)
        
        results = downloader.batch_download_sync(download_list)
        
        click.echo(f"\nDownload Summary:")
        click.echo(f"  Success: {results['success']}/{results['total']}")
        
        if results['failed']:
            click.echo(f"  Failed downloads:")
            for name in results['failed']:
                click.echo(f"    - {name}")
    else:
        # Save download list
        output_file = workflow_file.replace('.json', '_downloads.json')
        with open(output_file, 'w') as f:
            json.dump({'models': download_list}, f, indent=2)
        logger.info(f"Download list saved to: {output_file}")


@cli.command()
@click.option('--type', '-t', type=click.Choice(['search', 'model', 'general', 'all']),
              default='all', help='Cache type to clear')
def clear_cache(type):
    """Clear cached data."""
    cache_manager = CacheManager()
    
    if type == 'all':
        cache_manager.clear()
        logger.info("All caches cleared")
    else:
        cache_manager.clear(type)
        logger.info(f"{type.capitalize()} cache cleared")


@cli.command()
def cache_stats():
    """Show cache statistics."""
    cache_manager = CacheManager()
    stats = cache_manager.get_stats()
    
    click.echo("Cache Statistics:")
    click.echo(f"Cache directory: {stats['cache_dir']}")
    click.echo()
    
    for cache_type, info in stats['caches'].items():
        if 'error' in info:
            click.echo(f"{cache_type}: Error - {info['error']}")
        elif 'status' in info:
            click.echo(f"{cache_type}: {info['status']}")
        else:
            click.echo(f"{cache_type}:")
            click.echo(f"  File: {info['file']}")
            click.echo(f"  Size: {info['size_kb']:.1f} KB")
            click.echo(f"  Active entries: {info['active_entries']}")
            click.echo(f"  Expired entries: {info['expired_entries']}")


if __name__ == '__main__':
    cli()